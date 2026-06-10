// 购物车ViewModel
package com.rag.shopping.guide.ui.cart

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rag.shopping.guide.data.api.RetrofitClient
import com.rag.shopping.guide.data.model.CartAddRequest
import com.rag.shopping.guide.data.model.CartItem
import com.rag.shopping.guide.data.model.CartResponse
import com.rag.shopping.guide.data.model.CartUpdateRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class CartViewModel : ViewModel() {
    private val api = RetrofitClient.api

    private val _cart = MutableStateFlow(CartResponse(emptyList(), 0, 0.0))
    val cart: StateFlow<CartResponse> = _cart.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    fun loadCart() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                _cart.value = api.getCart()
            } catch (e: Exception) {
                _errorMessage.value = "加载购物车失败: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun addToCart(request: CartAddRequest) {
        viewModelScope.launch {
            try {
                api.addToCart(request)
                loadCart()
            } catch (e: Exception) {
                _errorMessage.value = "加购失败: ${e.message}"
            }
        }
    }

    fun updateQuantity(itemId: Int, qty: Int) {
        viewModelScope.launch {
            try {
                api.updateCartItem(itemId, CartUpdateRequest(qty))
                loadCart()
            } catch (e: Exception) {
                _errorMessage.value = "修改失败: ${e.message}"
            }
        }
    }

    fun removeItem(itemId: Int) {
        viewModelScope.launch {
            try {
                api.removeCartItem(itemId)
                loadCart()
            } catch (e: Exception) {
                _errorMessage.value = "删除失败: ${e.message}"
            }
        }
    }

    fun clearAll() {
        viewModelScope.launch {
            try {
                api.clearCart()
                loadCart()
            } catch (e: Exception) {
                _errorMessage.value = "清空购物车失败: ${e.message}"
            }
        }
    }

    fun clearError() {
        _errorMessage.value = null
    }
}
