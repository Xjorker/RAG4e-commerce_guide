// ChatUiState 数据模型
package com.rag.shopping.guide.data.model

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isLoading: Boolean = false,
    val sessionId: String = "",
    val recommendedProducts: List<ProductItem> = emptyList()
)
