// 客户端类目过滤工具 - 与后端 detect_target 逻辑保持一致
// 防御性过滤：即便后端过滤失效，客户端也能保证卡片不出现不相干类目
package com.rag.shopping.guide.util

object CategoryFilter {

    /**
     * 返回 (category, subcategory) 二元组
     * - 子品类优先（更精准），命中数最多获胜
     * - 子品类无命中时回退到大品类
     * - 都没有命中时返回 (null, null)
     */
    data class Target(val category: String?, val subcategory: String?)

    // 与后端 main.py 的 HIERARCHY 保持一致：类目 → 子品类 → 关键词列表
    private val HIERARCHY = mapOf(
        "数码电子" to mapOf(
            "智能手机" to listOf("手机", "iPhone", "iphone", "小米", "OPPO", "oppo", "vivo", "华为", "苹果",
                "5G", "智能机", "Mate", "Pura", "Reno", "Find", "Mix"),
            "平板电脑" to listOf("平板", "iPad", "ipad", "MatePad", "Pad", "Tab"),
            "笔记本电脑" to listOf("笔记本", "笔记本电脑", "MacBook", "macbook", "ThinkPad", "thinkpad",
                "MateBook", "ThinkBook", "Mac"),
            "真无线耳机" to listOf("耳机", "AirPods", "airpods", "FreeBuds", "freebuds", "蓝牙耳机",
                "降噪耳机", "入耳式", "头戴式", "有线耳机")
        ),
        "美妆护肤" to mapOf(
            "精华" to listOf("精华", "小棕瓶", "小灯泡", "小黑瓶", "安瓶"),
            "面霜" to listOf("面霜", "日霜", "晚霜", "面乳"),
            "眼霜" to listOf("眼霜", "眼部精华"),
            "面膜" to listOf("面膜", "面膜贴"),
            "洁面" to listOf("洁面", "洗面奶", "洁面乳", "洁面霜", "洁面慕斯", "洗颜专科"),
            "化妆水" to listOf("化妆水", "爽肤水", "粉水", "精华水", "收敛水"),
            "乳液" to listOf("乳液", "润肤乳"),
            "防晒" to listOf("防晒", "防晒霜", "防晒乳", "防晒喷雾"),
            "粉底液" to listOf("粉底液", "粉底", "粉底霜", "气垫", "BB霜"),
            "唇釉" to listOf("唇釉", "口红", "唇彩", "唇膏"),
            "眉笔" to listOf("眉笔", "眉粉", "眉膏"),
            "蜜粉" to listOf("蜜粉", "散粉", "定妆粉"),
            "卸妆" to listOf("卸妆", "卸妆水", "卸妆油", "卸妆膏")
        ),
        "食品饮料" to mapOf(
            "咖啡" to listOf("咖啡", "星巴克", "雀巢", "拿铁", "美式", "摩卡", "卡布奇诺"),
            "茶饮" to listOf("茶饮", "茶π", "乌龙茶", "绿茶", "红茶", "茉莉花茶", "柠檬茶", "果茶"),
            "功能饮料" to listOf("红牛", "脉动", "东鹏", "佳得乐"),
            "牛奶" to listOf("牛奶", "纯牛奶", "鲜奶", "高钙奶", "特仑苏", "金典", "脱脂奶"),
            "酸奶" to listOf("酸奶", "酸牛奶", "发酵乳"),
            "碳酸饮料" to listOf("可乐", "雪碧", "可口可乐", "百事可乐", "芬达", "醒目"),
            "方便食品" to listOf("方便面", "泡面", "拉面", "自热饭", "螺蛳粉", "速食", "自热火锅"),
            "坚果/零食" to listOf("零食", "坚果", "薯片", "巧克力", "饼干", "辣条", "锅巴", "果干"),
            "调味品" to listOf("调味品", "酱油", "醋", "料酒", "蚝油", "鸡精", "味精")
        ),
        "服饰运动" to mapOf(
            "跑步鞋" to listOf("跑步鞋", "跑鞋", "运动鞋", "运动"),
            "篮球鞋" to listOf("篮球鞋", "球鞋", "高帮"),
            "徒步鞋" to listOf("徒步鞋", "登山鞋", "户外鞋", "越野鞋"),
            "短袖T恤" to listOf("短袖", "T恤", "t恤", "短袖t恤"),
            "速干T恤" to listOf("速干", "速干衣", "速干T恤"),
            "运动长裤" to listOf("运动长裤", "运动裤", "健身裤"),
            "卫衣" to listOf("卫衣", "连帽衫"),
            "户外裤" to listOf("户外裤"),
            "瑜伽裤" to listOf("瑜伽裤"),
            "帽子" to listOf("帽子", "棒球帽", "渔夫帽", "鸭舌帽"),
            "背包" to listOf("背包", "双肩包", "登山包", "书包"),
            "运动短裤" to listOf("运动短裤", "健身短裤", "训练短裤")
        )
    )

    /**
     * 根据 query 推断目标 (类目, 子品类)
     */
    fun detect(query: String?): Target {
        if (query.isNullOrBlank()) return Target(null, null)
        val q = query.lowercase()

        // 1) 子品类优先
        var bestSub: String? = null
        var bestSubCat: String? = null
        var bestSubHits = 0
        for ((cat, subs) in HIERARCHY) {
            for ((sub, kws) in subs) {
                val unique = kws.map { it.lowercase() }.toSet()
                val hits = unique.count { it in q }
                if (hits > bestSubHits) {
                    bestSubHits = hits
                    bestSub = sub
                    bestSubCat = cat
                }
            }
        }
        if (bestSubHits > 0) {
            return Target(bestSubCat, bestSub)
        }

        // 2) 大品类兜底
        var bestCat: String? = null
        var bestCatHits = 0
        for ((cat, subs) in HIERARCHY) {
            val allKws = mutableSetOf<String>()
            for (kws in subs.values) {
                for (k in kws) allKws.add(k.lowercase())
            }
            val hits = allKws.count { it in q }
            if (hits > bestCatHits) {
                bestCatHits = hits
                bestCat = cat
            }
        }
        return Target(if (bestCatHits > 0) bestCat else null, null)
    }

    /**
     * 多轮回退：按顺序尝试 queries 中每个 query，第一个能命中类目的获胜
     * （用于"要更便宜的"这种没有类目关键词的 follow-up query）
     */
    fun detectWithFallback(queries: List<String?>): Target {
        for (q in queries) {
            val t = detect(q)
            if (t.category != null) return t
        }
        return Target(null, null)
    }
}
