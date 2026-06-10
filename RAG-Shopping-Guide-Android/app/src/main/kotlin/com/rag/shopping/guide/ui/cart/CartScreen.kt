// 购物车页面 - 含模拟下单确认流程
package com.rag.shopping.guide.ui.cart

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.LocationOn
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
import com.rag.shopping.guide.data.model.CartItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CartScreen(
    onBack: () -> Unit,
    onJumpToDetail: (String) -> Unit,
    viewModel: CartViewModel = viewModel()
) {
    val cart by viewModel.cart.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.errorMessage.collectAsState()

    var showCheckoutDialog by remember { mutableStateOf(false) }
    var orderSuccess by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.loadCart() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("购物车 (${cart.total_count})", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                }
            )
        },
        bottomBar = {
            if (cart.items.isNotEmpty()) {
                Surface(
                    tonalElevation = 8.dp,
                    color = MaterialTheme.colorScheme.surface
                ) {
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text("合计", fontSize = 12.sp, color = Color.Gray)
                            Text(
                                "¥${cart.total_amount}",
                                fontSize = 22.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                        Button(
                            onClick = { showCheckoutDialog = true },
                            modifier = Modifier.height(48.dp)
                        ) {
                            Text("去结算 (${cart.total_count})", fontSize = 16.sp)
                        }
                    }
                }
            }
        }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                isLoading && cart.items.isEmpty() -> {
                    CircularProgressIndicator(Modifier.align(Alignment.Center))
                }
                cart.items.isEmpty() -> {
                    Column(
                        Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Default.ShoppingCart,
                            contentDescription = null,
                            modifier = Modifier.size(80.dp),
                            tint = Color.LightGray
                        )
                        Spacer(Modifier.height(16.dp))
                        Text("购物车空空如也~", color = Color.Gray, fontSize = 16.sp)
                    }
                }
                else -> {
                    LazyColumn(
                        Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(cart.items) { item ->
                            CartItemRow(
                                item = item,
                                onQtyChange = { viewModel.updateQuantity(item.id, it) },
                                onRemove = { viewModel.removeItem(item.id) },
                                onClick = { onJumpToDetail(item.product_id) }
                            )
                        }
                    }
                }
            }

            error?.let { msg ->
                LaunchedEffect(msg) {
                    kotlinx.coroutines.delay(2500)
                    viewModel.clearError()
                }
                Snackbar(
                    Modifier.align(Alignment.BottomCenter).padding(16.dp)
                ) { Text(msg) }
            }
        }
    }

    // 下单确认弹窗
    if (showCheckoutDialog) {
        CheckoutDialog(
            cart = cart,
            onDismiss = { showCheckoutDialog = false },
            onConfirm = {
                showCheckoutDialog = false
                orderSuccess = true
                // 模拟下单：清空购物车
                viewModel.clearAll()
            }
        )
    }

    // 下单成功提示
    if (orderSuccess) {
        AlertDialog(
            onDismissRequest = { orderSuccess = false },
            icon = {
                Icon(
                    Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(48.dp)
                )
            },
            title = { Text("下单成功") },
            text = {
                Column {
                    Text("订单已提交，模拟完成下单闭环。")
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "共 ${cart.total_count} 件商品，金额 ¥${cart.total_amount}",
                        fontSize = 14.sp,
                        color = Color.Gray
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { orderSuccess = false }) { Text("好的") }
            }
        )
    }
}

@Composable
fun CheckoutDialog(
    cart: com.rag.shopping.guide.data.model.CartResponse,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("确认订单", fontWeight = FontWeight.Bold) },
        text = {
            Column {
                // 收货地址
                Row(verticalAlignment = Alignment.Top) {
                    Icon(
                        Icons.Default.LocationOn,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(Modifier.width(8.dp))
                    Column {
                        Text("收货人：张三  138****1234", fontSize = 14.sp, fontWeight = FontWeight.Medium)
                        Text(
                            "北京市朝阳区建国路88号 SOHO现代城 A座1801室",
                            fontSize = 13.sp,
                            color = Color.Gray
                        )
                    }
                }

                Divider(Modifier.padding(vertical = 12.dp))

                // 商品列表
                Text("商品清单", fontWeight = FontWeight.Medium, fontSize = 14.sp)
                Spacer(Modifier.height(8.dp))
                cart.items.take(3).forEach { item ->
                    Row(
                        Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            item.title,
                            fontSize = 13.sp,
                            maxLines = 1,
                            modifier = Modifier.weight(1f)
                        )
                        Text(
                            "x${item.quantity}",
                            fontSize = 13.sp,
                            color = Color.Gray
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "¥${item.subtotal}",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
                if (cart.items.size > 3) {
                    Text(
                        "等共 ${cart.items.size} 种商品",
                        fontSize = 12.sp,
                        color = Color.Gray,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }

                Divider(Modifier.padding(vertical = 12.dp))

                // 金额汇总
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("商品总数", fontSize = 13.sp, color = Color.Gray)
                    Text("${cart.total_count} 件", fontSize = 13.sp)
                }
                Spacer(Modifier.height(4.dp))
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("运费", fontSize = 13.sp, color = Color.Gray)
                    Text("免运费", fontSize = 13.sp, color = MaterialTheme.colorScheme.primary)
                }
                Spacer(Modifier.height(8.dp))
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("应付金额", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Text(
                        "¥${cart.total_amount}",
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        },
        confirmButton = {
            Button(onClick = onConfirm) { Text("确认下单") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("再想想") }
        }
    )
}

@Composable
fun CartItemRow(
    item: CartItem,
    onQtyChange: (Int) -> Unit,
    onRemove: () -> Unit,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        onClick = onClick
    ) {
        Row(
            Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 商品图
            AsyncImage(
                model = "file:///android_asset/${item.image_path}",
                contentDescription = item.title,
                modifier = Modifier
                    .size(80.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color.LightGray),
                contentScale = ContentScale.Crop
            )
            Spacer(Modifier.width(12.dp))

            Column(Modifier.weight(1f)) {
                Text(
                    item.title,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 2
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "¥${item.unit_price}",
                    color = MaterialTheme.colorScheme.primary,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(4.dp))
                // 数量加减
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedIconButton(
                        onClick = { if (item.quantity > 1) onQtyChange(item.quantity - 1) },
                        modifier = Modifier.size(28.dp)
                    ) { Text("-", fontSize = 14.sp) }
                    Text(
                        "${item.quantity}",
                        Modifier.padding(horizontal = 12.dp),
                        fontWeight = FontWeight.Bold
                    )
                    OutlinedIconButton(
                        onClick = { onQtyChange(item.quantity + 1) },
                        modifier = Modifier.size(28.dp)
                    ) { Text("+", fontSize = 14.sp) }
                }
            }
            IconButton(onClick = onRemove) {
                Icon(
                    Icons.Default.Delete,
                    contentDescription = "删除",
                    tint = Color.Gray
                )
            }
        }
    }
}
