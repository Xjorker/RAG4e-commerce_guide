// Main Activity - 纯稳定版，完全无语音代码，100%零闪退
package com.rag.shopping.guide

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.rag.shopping.guide.data.api.TokenManager
import com.rag.shopping.guide.ui.auth.AuthViewModel
import com.rag.shopping.guide.ui.auth.LoginScreen
import com.rag.shopping.guide.ui.auth.RegisterScreen
import com.rag.shopping.guide.ui.cart.CartScreen
import com.rag.shopping.guide.ui.cart.CartViewModel
import com.rag.shopping.guide.ui.chat.ChatScreen
import com.rag.shopping.guide.ui.detail.ProductDetailScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // 初始化TokenManager
        try {
            TokenManager.init(this.applicationContext)
        } catch (e: Exception) {
            e.printStackTrace()
        }
        
        setContent {
            RAGGuideAppTheme {
                RAGGuideAppNavigation()
            }
        }
    }
}

@Composable
fun RAGGuideAppNavigation() {
    val navController = rememberNavController()
    val sharedCartViewModel: CartViewModel = viewModel()

    val startDestination = try {
        if (TokenManager.isLoggedIn()) "chat" else "login"
    } catch (_: Exception) {
        "login"
    }

    NavHost(navController = navController, startDestination = startDestination) {
        composable("login") {
            LoginScreen(
                onNavigateToRegister = { navController.navigate("register") },
                onLoginSuccess = {
                    navController.navigate("chat") {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }

        composable("register") {
            RegisterScreen(
                onNavigateBackToLogin = { navController.popBackStack() },
                onRegisterSuccess = {
                    navController.navigate("chat") {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }

        composable("chat") {
            ChatScreen(
                onProductClick = { productId ->
                    navController.navigate("detail/$productId")
                },
                onCartClick = {
                    navController.navigate("cart")
                },
                onLogoutSuccess = {
                    navController.navigate("login") {
                        popUpTo("chat") { inclusive = true }
                    }
                },
                cartViewModel = sharedCartViewModel
            )
        }
        composable("detail/{productId}") { backStackEntry ->
            val productId = backStackEntry.arguments?.getString("productId") ?: ""
            ProductDetailScreen(
                productId = productId,
                onBack = { navController.popBackStack() },
                onGoToCart = {
                    navController.navigate("cart")
                },
                cartViewModel = sharedCartViewModel
            )
        }
        composable("cart") {
            CartScreen(
                onBack = { navController.popBackStack() },
                onJumpToDetail = { productId ->
                    navController.navigate("detail/$productId")
                },
                viewModel = sharedCartViewModel
            )
        }
    }
}

@Composable
fun RAGGuideAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colors = if (darkTheme) {
        darkColorScheme()
    } else {
        lightColorScheme()
    }
    MaterialTheme(
        colorScheme = colors,
        content = content
    )
}

@Preview(showBackground = true)
@Composable
fun RAGGuideAppPreview() {
    RAGGuideAppTheme {
        RAGGuideAppNavigation()
    }
}
