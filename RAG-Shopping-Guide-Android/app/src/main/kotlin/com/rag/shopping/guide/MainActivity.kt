// Main Activity - 包含共享购物车ViewModel的导航图
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
import com.rag.shopping.guide.ui.cart.CartScreen
import com.rag.shopping.guide.ui.cart.CartViewModel
import com.rag.shopping.guide.ui.chat.ChatScreen
import com.rag.shopping.guide.ui.detail.ProductDetailScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
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
    // 共享同一个 CartViewModel 实例，让角标在多屏之间同步
    val sharedCartViewModel: CartViewModel = viewModel()

    NavHost(navController = navController, startDestination = "chat") {
        composable("chat") {
            ChatScreen(
                onProductClick = { productId ->
                    navController.navigate("detail/$productId")
                },
                onCartClick = {
                    navController.navigate("cart")
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
