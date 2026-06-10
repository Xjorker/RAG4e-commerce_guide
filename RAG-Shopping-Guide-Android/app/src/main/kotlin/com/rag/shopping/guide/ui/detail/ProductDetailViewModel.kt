// 商品详情ViewModel
package com.rag.shopping.guide.ui.detail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewModelScope
import com.rag.shopping.guide.data.api.RetrofitClient
import com.rag.shopping.guide.data.model.CartAddRequest
import com.rag.shopping.guide.data.model.Sku
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ProductDetailState(
    val product: com.rag.shopping.guide.data.model.Product? = null,
    val skus: List<Sku> = emptyList(),
    val selectedSku: Sku? = null,
    val quantity: Int = 1,
    val isLoading: Boolean = false,
    val message: String? = null
)

class ProductDetailViewModel : ViewModel() {
    private val api = RetrofitClient.api

    private val _state = MutableStateFlow(ProductDetailState())
    val state: StateFlow<ProductDetailState> = _state.asStateFlow()

    fun loadProduct(productId: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, message = null)
            try {
                val resp = api.getProduct(productId)
                _state.value = _state.value.copy(
                    product = resp.product,
                    skus = resp.skus,
                    selectedSku = resp.skus.firstOrNull(),
                    isLoading = false
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isLoading = false,
                    message = "加载商品失败: ${e.message}"
                )
            }
        }
    }

    fun selectSku(sku: Sku) {
        _state.value = _state.value.copy(selectedSku = sku)
    }

    fun changeQuantity(qty: Int) {
        if (qty in 1..99) _state.value = _state.value.copy(quantity = qty)
    }

    fun addToCart() {
        val p = _state.value.product ?: return
        val sku = _state.value.selectedSku
        viewModelScope.launch {
            try {
                api.addToCart(CartAddRequest(
                    product_id = p.product_id,
                    sku_id = sku?.sku_id,
                    title = p.title,
                    brand = p.brand,
                    image_path = p.image_path,
                    unit_price = sku?.price ?: p.base_price,
                    quantity = _state.value.quantity
                ))
                _state.value = _state.value.copy(message = "已加入购物车")
            } catch (e: Exception) {
                _state.value = _state.value.copy(message = "加购失败: ${e.message}")
            }
        }
    }

    fun clearMessage() {
        _state.value = _state.value.copy(message = null)
    }
}
