// 商品详情页面
package com.rag.shopping.guide.ui.detail

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.rag.shopping.guide.data.model.Sku
import com.rag.shopping.guide.ui.cart.CartViewModel

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun ProductDetailScreen(
    productId: String,
    onBack: () -> Unit,
    onGoToCart: () -> Unit,
    viewModel: ProductDetailViewModel = viewModel(),
    cartViewModel: CartViewModel = viewModel()
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(productId) {
        viewModel.loadProduct(productId)
    }

    val message = state.message
    LaunchedEffect(message) {
        if (message != null) {
            kotlinx.coroutines.delay(1500)
            viewModel.clearMessage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("商品详情", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    IconButton(onClick = onGoToCart) {
                        Icon(Icons.Default.ShoppingCart, contentDescription = "购物车")
                    }
                }
            )
        },
        bottomBar = {
            if (state.product != null) {
                Surface(tonalElevation = 8.dp, color = MaterialTheme.colorScheme.surface) {
                    Row(
                        Modifier.fillMaxWidth().padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        OutlinedButton(
                            onClick = onGoToCart,
                            modifier = Modifier.weight(1f).height(48.dp)
                        ) {
                            Text("购物车")
                        }
                        Button(
                            onClick = {
                                viewModel.addToCart()
                            },
                            modifier = Modifier.weight(2f).height(48.dp)
                        ) {
                            Text("加入购物车", fontSize = 16.sp)
                        }
                    }
                }
            }
        }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            if (state.isLoading) {
                CircularProgressIndicator(Modifier.align(Alignment.Center))
            } else if (state.product == null) {
                Text(
                    "商品不存在",
                    Modifier.align(Alignment.Center),
                    color = Color.Gray
                )
            } else {
                val product = state.product!!
                val skus = state.skus
                val selectedSku = state.selectedSku ?: skus.firstOrNull()

                Column(
                    Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                ) {
                    // 商品大图
                    AsyncImage(
                        model = "file:///android_asset/${product.image_path}",
                        contentDescription = product.title,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(360.dp)
                            .background(Color.White),
                        contentScale = ContentScale.Fit
                    )

                    Column(Modifier.padding(16.dp)) {
                        // 品牌
                        if (product.brand.isNotBlank()) {
                            Text(
                                product.brand,
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 13.sp
                            )
                            Spacer(Modifier.height(4.dp))
                        }

                        // 标题
                        Text(
                            product.title,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(Modifier.height(8.dp))

                        // 分类
                        Text(
                            "${product.category} / ${product.sub_category}",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                        Spacer(Modifier.height(12.dp))

                        // 价格
                        Text(
                            "¥${selectedSku?.price ?: product.base_price}",
                            color = MaterialTheme.colorScheme.primary,
                            fontSize = 26.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(Modifier.height(16.dp))

                        // SKU选择器
                        if (skus.isNotEmpty()) {
                            Text("规格", fontWeight = FontWeight.Medium, fontSize = 14.sp)
                            Spacer(Modifier.height(8.dp))
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                skus.forEach { sku ->
                                    SkuChip(
                                        sku = sku,
                                        selected = selectedSku?.sku_id == sku.sku_id,
                                        onClick = { viewModel.selectSku(sku) }
                                    )
                                }
                            }
                            Spacer(Modifier.height(16.dp))
                        }

                        // 数量
                        Text("数量", fontWeight = FontWeight.Medium, fontSize = 14.sp)
                        Spacer(Modifier.height(8.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            OutlinedIconButton(
                                onClick = { viewModel.changeQuantity(state.quantity - 1) }
                            ) { Text("-", fontSize = 18.sp) }
                            Text(
                                "${state.quantity}",
                                Modifier.padding(horizontal = 16.dp),
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                            OutlinedIconButton(
                                onClick = { viewModel.changeQuantity(state.quantity + 1) }
                            ) { Text("+", fontSize = 18.sp) }
                        }
                        Spacer(Modifier.height(24.dp))

                        // 描述（占位）
                        Text("商品介绍", fontWeight = FontWeight.Medium, fontSize = 14.sp)
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "本商品为" + product.brand + "旗下" + product.sub_category + "品类，提供" + skus.size + "种规格选择。通过对话咨询我们的AI导购，可获取更详细的产品成分、使用建议、搭配方案。",
                            fontSize = 14.sp,
                            color = Color.DarkGray,
                            lineHeight = 20.sp
                        )
                        Spacer(Modifier.height(80.dp))
                    }
                }
            }

            // 提示信息
            message?.let { msg ->
                Snackbar(
                    Modifier.align(Alignment.BottomCenter).padding(16.dp)
                ) { Text(msg) }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SkuChip(sku: Sku, selected: Boolean, onClick: () -> Unit) {
    val label = sku.properties.entries.joinToString(" / ") { it.value.toString() }
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text("$label ¥${sku.price}") }
    )
}
