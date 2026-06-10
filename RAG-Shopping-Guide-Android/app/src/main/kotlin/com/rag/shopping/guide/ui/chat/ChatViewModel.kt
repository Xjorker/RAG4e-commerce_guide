// Chat ViewModel - 支持SSE流式回复 + 新建会话 + Agent自动加购刷新购物车
package com.rag.shopping.guide.ui.chat

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rag.shopping.guide.data.api.RetrofitClient
import com.rag.shopping.guide.data.api.SSEClientFactory
import com.rag.shopping.guide.data.model.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class ChatViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private val api = RetrofitClient.api
    private val sseClient = SSEClientFactory.create("http://10.0.2.2:9000")

    // 回调：当Agent自动加购成功后通知外部刷新购物车
    var onCartChanged: (() -> Unit)? = null

    init {
        _uiState.value = _uiState.value.copy(
            sessionId = generateSessionId()
        )
    }

    private fun generateSessionId(): String {
        return "session_" + System.currentTimeMillis().toString()
    }

    fun startNewSession() {
        // 新建会话：清空全部历史消息 + 生成全新的 session_id
        _uiState.value = _uiState.value.copy(
            messages = emptyList(),
            recommendedProducts = emptyList(),
            sessionId = generateSessionId(),
            isLoading = false
        )
    }

    fun sendMessage(query: String) {
        val currentMessages = _uiState.value.messages.toMutableList()
        val userMsg = ChatMessage(
            id = "msg_" + System.currentTimeMillis().toString(),
            role = "user",
            content = query
        )
        currentMessages.add(userMsg)

        val streamingId = "msg_" + (System.currentTimeMillis() + 1).toString()
        val streamingMsg = ChatMessage(
            id = streamingId,
            role = "assistant",
            content = "",
            products = emptyList(),
            isStreaming = true
        )
        currentMessages.add(streamingMsg)

        _uiState.value = _uiState.value.copy(
            messages = currentMessages,
            isLoading = true
        )

        viewModelScope.launch {
            try {
                val historyList = currentMessages.takeLast(6).map {
                    mapOf("role" to it.role, "content" to it.content)
                }

                val request = ChatRequest(
                    session_id = _uiState.value.sessionId,
                    query = query,
                    history = historyList
                )

                var accumulatedContent = ""
                var currentProducts = emptyList<ProductItem>()

                sseClient.streamChat(request).collectLatest { event ->
                    when (event) {
                        is SSEEvent.Session -> {
                            _uiState.value = _uiState.value.copy(
                                sessionId = event.sessionId
                            )
                        }
                        is SSEEvent.Content -> {
                            accumulatedContent += event.delta
                            val freshMsgs = _uiState.value.messages.toMutableList()
                            val idx = freshMsgs.indexOfFirst { it.id == streamingId }
                            if (idx >= 0) {
                                freshMsgs[idx] = freshMsgs[idx].copy(
                                    content = accumulatedContent,
                                    products = currentProducts,
                                    isStreaming = true
                                )
                                _uiState.value = _uiState.value.copy(messages = freshMsgs)
                            }
                        }
                        is SSEEvent.Products -> {
                            currentProducts = event.products
                            val freshMsgs = _uiState.value.messages.toMutableList()
                            val idx = freshMsgs.indexOfFirst { it.id == streamingId }
                            if (idx >= 0) {
                                freshMsgs[idx] = freshMsgs[idx].copy(
                                    content = accumulatedContent,
                                    products = currentProducts,
                                    isStreaming = true
                                )
                                _uiState.value = _uiState.value.copy(
                                    messages = freshMsgs
                                )
                            }
                        }
                        is SSEEvent.CartAction -> {
                            // Agent自动加购事件收到！如果加购成功通知外部刷新购物车
                            if (event.added_to_cart && event.cart_item_id != null) {
                                onCartChanged?.invoke()
                            }
                        }
                        is SSEEvent.Done -> {
                            val freshMsgs = _uiState.value.messages.toMutableList()
                            val idx = freshMsgs.indexOfFirst { it.id == streamingId }
                            if (idx >= 0) {
                                freshMsgs[idx] = freshMsgs[idx].copy(
                                    content = accumulatedContent,
                                    products = currentProducts,
                                    isStreaming = false
                                )
                                _uiState.value = _uiState.value.copy(
                                    messages = freshMsgs,
                                    isLoading = false
                                )
                            }
                        }
                        is SSEEvent.Error -> {
                            val freshMsgs = _uiState.value.messages.toMutableList()
                            val idx = freshMsgs.indexOfFirst { it.id == streamingId }
                            if (idx >= 0) {
                                freshMsgs[idx] = freshMsgs[idx].copy(
                                    content = "抱歉，连接出错: " + event.message,
                                    isStreaming = false
                                )
                                _uiState.value = _uiState.value.copy(
                                    messages = freshMsgs,
                                    isLoading = false
                                )
                            }
                        }
                    }
                }

            } catch (e: Exception) {
                val idx = _uiState.value.messages.indexOfFirst { it.id == streamingId }
                val msgs = _uiState.value.messages.toMutableList()
                if (idx >= 0) {
                    msgs[idx] = msgs[idx].copy(
                        content = "抱歉，网络出错了: " + e.message,
                        isStreaming = false
                    )
                }
                _uiState.value = _uiState.value.copy(
                    messages = msgs,
                    isLoading = false
                )
            }
        }
    }

    fun searchByImage(context: Context, imageUri: Uri, queryText: String? = null) {
        _uiState.value = _uiState.value.copy(isLoading = true)

        viewModelScope.launch {
            try {
                val tempFile = File(context.cacheDir, "temp_search_image.jpg")
                context.contentResolver.openInputStream(imageUri)?.use { input ->
                    tempFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }

                val requestFile = tempFile.asRequestBody(
                    contentType = "image/jpeg".toMediaType()
                )
                val body = MultipartBody.Part.createFormData(
                    "image", tempFile.name, requestFile
                )

                val response = api.searchByImage(
                    image = body,
                    query = queryText ?: ""
                )

                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    recommendedProducts = response.results.map {
                        ProductItem(it.product, it.skus)
                    }
                )

            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false
                )
            }
        }
    }
}
