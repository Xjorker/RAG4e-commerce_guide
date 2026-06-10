// AuthViewModel - 登录注册状态管理
package com.rag.shopping.guide.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rag.shopping.guide.data.api.RetrofitClient
import com.rag.shopping.guide.data.api.TokenManager
import com.rag.shopping.guide.data.model.AuthRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AuthViewModel : ViewModel() {
    private val api = RetrofitClient.api

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _isLoggedIn = MutableStateFlow(TokenManager.isLoggedIn())
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()

    fun register(username: String, password: String, nickname: String? = null, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val resp = api.register(AuthRequest(username, password, nickname))
                if (resp.ok && !resp.token.isNullOrEmpty()) {
                    TokenManager.saveToken(resp.token!!, resp.user_id, resp.username)
                    _isLoggedIn.value = true
                    onSuccess()
                } else {
                    _errorMessage.value = resp.error ?: resp.detail ?: "注册失败"
                }
            } catch (e: Exception) {
                _errorMessage.value = "注册出错: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun login(username: String, password: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val resp = api.login(AuthRequest(username, password))
                if (resp.ok && !resp.token.isNullOrEmpty()) {
                    TokenManager.saveToken(resp.token!!, resp.user_id, resp.username)
                    _isLoggedIn.value = true
                    onSuccess()
                } else {
                    _errorMessage.value = resp.error ?: resp.detail ?: "登录失败"
                }
            } catch (e: Exception) {
                _errorMessage.value = "登录出错: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun logout(onSuccess: () -> Unit) {
        viewModelScope.launch {
            try {
                api.logout()
            } catch (ignored: Exception) {
                // 忽略登出时网络异常，直接本地清除
            }
            TokenManager.clear()
            _isLoggedIn.value = false
            onSuccess()
        }
    }

    fun clearError() {
        _errorMessage.value = null
    }
}
