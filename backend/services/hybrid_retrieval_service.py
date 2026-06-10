import numpy as np
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional
from config import settings
from database import chroma_client, bm25_index_manager, sqlite_client

class HybridRetrievalService:
    def __init__(self):
        self.vector_weight = settings.RETRIEVAL_VECTOR_WEIGHT
        self.bm25_weight = settings.RETRIEVAL_BM25_WEIGHT
        self.top_k = settings.RETRIEVAL_TOP_K
        self.initial_top_k = settings.RETRIEVAL_INITIAL_TOP_K
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        if not scores:
            return []
        min_s = min(scores)
        max_s = max(scores)
        if max_s - min_s == 0:
            return [0.0 for _ in scores]
        return [(s - min_s) / (max_s - min_s) for s in scores]
    
    def hybrid_search(self, query_text: str, query_embedding: List[float], target_category: Optional[str] = None, target_sub: Optional[str] = None, price_sensitive: bool = False) -> List[Dict[str, Any]]:
        fragments_map = {}
        all_fragments = sqlite_client.get_all_fragments()
        for frag in all_fragments:
            fragments_map[frag['fragment_id']] = frag

        chroma_results = chroma_client.query_embedding(query_embedding, n_results=self.initial_top_k)
        vector_hits = []
        if chroma_results and 'ids' in chroma_results and chroma_results['ids'] and len(chroma_results['ids']) > 0:
            for idx, fid in enumerate(chroma_results['ids'][0]):
                distance = chroma_results['distances'][0][idx]
                score = 1.0 - distance
                vector_hits.append((fid, score, chroma_results['metadatas'][0][idx]))

        bm25_hits = bm25_index_manager.query(query_text, top_k=self.initial_top_k)

        all_items = {}
        for fid, sc, meta in vector_hits:
            all_items[fid] = {
                "vector_score": sc,
                "bm25_score": 0.0,
                "meta": meta
            }

        for fid, sc in bm25_hits:
            if fid in all_items:
                all_items[fid]["bm25_score"] = sc
            else:
                all_items[fid] = {
                    "vector_score": 0.0,
                    "bm25_score": sc,
                    "meta": None
                }

        v_scores_list = []
        b_scores_list = []
        for fid in all_items:
            v_scores_list.append(all_items[fid]["vector_score"])
            b_scores_list.append(all_items[fid]["bm25_score"])

        v_norm = self._normalize_scores(v_scores_list)
        b_norm = self._normalize_scores(b_scores_list)

        fused = []
        idx = 0
        for fid in all_items:
            vs = v_norm[idx] if idx < len(v_norm) else 0.0
            bs = b_norm[idx] if idx < len(b_norm) else 0.0
            final_score = self.vector_weight * vs + self.bm25_weight * bs
            fused.append((fid, final_score, all_items[fid]["meta"]))
            idx += 1

        fused_sorted = sorted(fused, key=lambda x: x[1], reverse=True)

        # 场景1：target_sub 已指定 → 100% 全量硬过滤该子分类所有商品，向量召回漏了也从DB兜底
        if target_sub is not None:
            # 第一步：先从 全数据库 捞该子分类下的所有商品
            all_valid_products_full = [p for p in sqlite_client.get_all_products() if p.get("sub_category") == target_sub]
            if not all_valid_products_full:
                return []

            kept_pids_set = set()
            result = []

            # 第二步：把向量/BM25召回中的该子分类商品，按原始score 加入
            for fid, score, meta in fused_sorted:
                tmp_pid = None
                if fid in fragments_map:
                    tmp_pid = fragments_map[fid].get('product_id')
                elif meta and "product_id" in meta:
                    tmp_pid = meta["product_id"]
                if not tmp_pid:
                    continue
                if tmp_pid in kept_pids_set:
                    continue
                tmp_prod = sqlite_client.get_product_by_id(tmp_pid)
                if not tmp_prod:
                    continue
                if tmp_prod.get("sub_category") != target_sub:
                    continue  # 完全排除！不相干商品绝对不能进来
                tmp_frag = fragments_map.get(fid)
                skus = sqlite_client.get_skus_by_product_id(tmp_pid)
                result.append({
                    "fragment_id": fid,
                    "score": score,
                    "fragment": tmp_frag if tmp_frag else {"fragment_id": fid, "product_id": tmp_pid, "content_type": "image", "title": "", "content": "商品图片"},
                    "product": tmp_prod,
                    "skus": skus
                })
                kept_pids_set.add(tmp_pid)

            # 第三步：从全数据库 补全 所有向量召回没捞到的该子分类商品
            for p in all_valid_products_full:
                pid = p.get("product_id")
                if pid in kept_pids_set:
                    continue
                frag = sqlite_client.get_fragments_by_product_id(pid)
                if not frag:
                    continue
                skus = sqlite_client.get_skus_by_product_id(pid)
                result.append({
                    "fragment_id": frag["fragment_id"],
                    "score": 0.0,
                    "fragment": frag,
                    "product": p,
                    "skus": skus
                })
                kept_pids_set.add(pid)

            print(f"[AbsoluteHardFilter] target_sub='{target_sub}' total={len(result)} products (all from full DB)")

            # 第四步：排序：价格敏感 → 100% base_price 升序；否则 score 降序
            if price_sensitive:
                result.sort(key=lambda x: x["product"].get("base_price") or float("inf"))
                cheapest = result[0]["product"]
                print(f"[PriceSensitiveFinal] cheapest=¥{cheapest.get('base_price'):.0f} {cheapest.get('title')}")
            else:
                result.sort(key=lambda x: x["score"], reverse=True)

            return result[:self.top_k]

        # 场景2：target_sub 没指定 → 老逻辑兜底
        anchor_category = target_category
        has_anchor = bool(anchor_category)

        top_results = []
        added_product_ids = set()
        last_category = anchor_category

        for fid, score, meta in fused_sorted:
            product_id = None
            frag_data = None

            if fid in fragments_map:
                frag_data = fragments_map[fid]
                product_id = frag_data['product_id']
            elif meta and "product_id" in meta:
                product_id = meta["product_id"]

            if product_id is None:
                continue

            if product_id not in added_product_ids:
                full_product = sqlite_client.get_product_by_id(product_id)
                if full_product is None:
                    continue

                current_category = full_product.get("category", "")

                if has_anchor:
                    if current_category != anchor_category:
                        score = score * 0.5
                else:
                    if last_category is not None and last_category != current_category:
                        score = score * 0.3
                    if last_category is None and full_product is not None:
                        last_category = current_category

                skus = sqlite_client.get_skus_by_product_id(product_id)

                top_results.append({
                    "fragment_id": fid,
                    "score": score,
                    "fragment": frag_data if frag_data is not None else {
                        "fragment_id": fid,
                        "product_id": product_id,
                        "content_type": "image",
                        "title": "",
                        "content": "商品图片"
                    },
                    "product": full_product,
                    "skus": skus
                })

                added_product_ids.add(product_id)

                if len(top_results) >= self.top_k:
                    break

        top_results = sorted(top_results, key=lambda x: x["score"], reverse=True)[:self.top_k]
        return top_results

hybrid_retrieval_service = HybridRetrievalService()
