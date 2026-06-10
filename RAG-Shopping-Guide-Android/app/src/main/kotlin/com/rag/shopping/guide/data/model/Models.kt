// 数据模型
package com.rag.shopping.guide.data.model

data class ChatRequest(
    val session_id: String = "",
    val query: String,
    val history: List<Map<String, String>>? = null
)

data class ChatResponse(
    val ai_reply: String,
    val products: List<ProductItem>,
    val session_id: String,
    val history: List<Map<String, String>>? = null,
    val cart_action: CartAction? = null,
    val exclude_keywords: List<String>? = null
)

data class CartAction(
    val intent_detected: Boolean,
    val keyword: String?,
    val product_id: String?,
    val title: String?,
    val added_to_cart: Boolean,
    val cart_item_id: Int? = null,
    val error: String? = null
)

data class CartItem(
    val id: Int,
    val user_id: String,
    val product_id: String,
    val sku_id: String?,
    val title: String,
    val brand: String?,
    val image_path: String?,
    val unit_price: Double,
    val quantity: Int,
    val subtotal: Double,
    val added_at: String
)

data class CartResponse(
    val items: List<CartItem>,
    val total_count: Int,
    val total_amount: Double
)

data class CartAddRequest(
    val user_id: String = "default_user",
    val product_id: String,
    val sku_id: String? = null,
    val title: String,
    val brand: String? = null,
    val image_path: String? = null,
    val unit_price: Double,
    val quantity: Int = 1
)

data class CartUpdateRequest(
    val quantity: Int
)

data class ProductItem(
    val product: Product,
    val skus: List<Sku>,
    val score: Double = 0.0
)

data class Product(
    val product_id: String,
    val title: String,
    val brand: String,
    val category: String,
    val sub_category: String,
    val base_price: Double,
    val image_path: String?
)

data class Sku(
    val sku_id: String,
    val product_id: String,
    val properties: Map<String, Any>,
    val price: Double
)

data class SearchRequest(
    val query: String
)

data class SearchResponse(
    val results: List<SearchResultItem>,
    val image_filename: String? = null,
    val query_text: String? = null
)

data class SearchResultItem(
    val fragment_id: String,
    val score: Double,
    val fragment: FragmentItem,
    val product: Product,
    val skus: List<Sku>
)

data class FragmentItem(
    val fragment_id: String,
    val product_id: String,
    val content_type: String,
    val title: String?,
    val content: String
)

data class GetProductResponse(
    val product: Product,
    val skus: List<Sku>
)

data class ChatMessage(
    val id: String,
    val role: String,
    val content: String,
    val products: List<ProductItem> = emptyList(),
    val isStreaming: Boolean = false,
    val timestamp: Long = System.currentTimeMillis()
)

// SSE流式事件模型
sealed class SSEEvent {
    data class Session(val sessionId: String) : SSEEvent()
    data class Content(val delta: String) : SSEEvent()
    data class Products(val products: List<ProductItem>) : SSEEvent()
    data class CartAction(
        val intent_detected: Boolean,
        val keyword: String? = null,
        val product_id: String? = null,
        val title: String? = null,
        val added_to_cart: Boolean,
        val cart_item_id: Int? = null,
        val error: String? = null
    ) : SSEEvent()
    data class Done(val sessionId: String) : SSEEvent()
    data class Error(val message: String) : SSEEvent()
}

// ========== 登录注册 ==========
data class AuthRequest(
    val username: String,
    val password: String,
    val nickname: String? = null
)

data class AuthResponse(
    val ok: Boolean,
    val token: String? = null,
    val user_id: Int? = null,
    val username: String? = null,
    val nickname: String? = null,
    val expires_at: String? = null,
    val error: String? = null,
    val detail: String? = null
)

data class MeResponse(
    val ok: Boolean,
    val user_id: String? = null
)
