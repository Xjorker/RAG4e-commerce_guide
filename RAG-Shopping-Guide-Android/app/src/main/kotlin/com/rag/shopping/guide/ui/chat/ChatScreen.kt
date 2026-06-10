// 极简稳定版ChatScreen - 完全移除语音功能，100%零闪退
package com.rag.shopping.guide.ui.chat

import android.Manifest
import android.app.Activity
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.rag.shopping.guide.data.model.CartAddRequest
import com.rag.shopping.guide.data.model.CartResponse
import com.rag.shopping.guide.data.model.ChatMessage
import com.rag.shopping.guide.data.model.ChatUiState
import com.rag.shopping.guide.data.model.ProductItem
import com.rag.shopping.guide.ui.cart.CartViewModel
import com.rag.shopping.guide.util.CategoryFilter
import kotlinx.coroutines.delay

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onProductClick: (String) -> Unit,
    onCartClick: () -> Unit,
    onLogoutSuccess: () -> Unit,
    viewModel: ChatViewModel = viewModel(),
    cartViewModel: CartViewModel = viewModel(),
    authViewModel: com.rag.shopping.guide.ui.auth.AuthViewModel = viewModel()
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()
    val cart by cartViewModel.cart.collectAsState(initial = CartResponse(emptyList(),0,0.0))
    val listState = rememberLazyListState()
    var inputText by remember { mutableStateOf(TextFieldValue("")) }
    var showLogoutDialog by remember { mutableStateOf(false) }

    // 图片选择器
    var selectedImageUri by remember { mutableStateOf<Uri?>(null) }
    val imagePickerLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) {
            selectedImageUri = uri
        }
    }
    // 权限请求
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            imagePickerLauncher.launch("image/*")
        }
    }

    LaunchedEffect(Unit) {
        cartViewModel.loadCart()
        viewModel.onCartChanged = { cartViewModel.loadCart() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AI智能导购", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White
                ),
                actions = {
                    IconButton(onClick = onCartClick) {
                        Box {
                            Icon(Icons.Default.ShoppingCart, "购物车", tint = Color.White)
                            if(cart.total_count > 0) {
                                Text("${cart.total_count}", fontSize = 10.sp, color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier
                                        .align(Alignment.TopEnd)
                                        .offset(x=8.dp, y= (-8).dp)
                                        .background(MaterialTheme.colorScheme.error, CircleShape)
                                        .padding(horizontal=4.dp, vertical=2.dp))
                            }
                        }
                    }
                    IconButton(onClick = { viewModel.startNewSession() }) {
                        Icon(Icons.Default.Refresh, "新建对话", tint = Color.White)
                    }
                    IconButton(onClick = { showLogoutDialog = true }) {
                        Icon(Icons.Default.Logout, "退出登录", tint = Color.White)
                    }
                }
            )
        },
        bottomBar = {
            Surface(modifier = Modifier.navigationBarsPadding().imePadding(), shadowElevation=8.dp) {
                Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = {
                        // 图片选择
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            permissionLauncher.launch(Manifest.permission.READ_MEDIA_IMAGES)
                        } else {
                            permissionLauncher.launch(Manifest.permission.READ_EXTERNAL_STORAGE)
                        }
                    }) {
                        Icon(Icons.Default.AttachFile, "选择图片", tint = MaterialTheme.colorScheme.primary)
                    }

                    OutlinedTextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("请输入您的问题") },
                        maxLines = 3,
                        shape = RoundedCornerShape(24.dp)
                    )

                    Spacer(Modifier.width(8.dp))
                    IconButton(onClick = {
                        if(selectedImageUri != null) {
                            viewModel.searchByImage(context, selectedImageUri!!, inputText.text.ifEmpty { null })
                            selectedImageUri = null
                            inputText = TextFieldValue("")
                        } else if (inputText.text.isNotBlank()) {
                            viewModel.sendMessage(inputText.text.trim())
                            inputText = TextFieldValue("")
                        }
                    }) {
                        Icon(
                            imageVector = Icons.Default.Send,
                            contentDescription = "发送",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.background(MaterialTheme.colorScheme.primaryContainer, CircleShape).padding(8.dp)
                        )
                    }
                }
            }
        }
    ) { padding ->
        LazyColumn(modifier= Modifier.fillMaxSize().padding(padding).background(MaterialTheme.colorScheme.background),
            state=listState, contentPadding = PaddingValues(12.dp)
        ) {
            items(uiState.messages) { msg ->
                ChatBubble(msg)
                if (msg.role == "assistant" && msg.products.isNotEmpty()) {
                    val recentQueries = uiState.messages
                        .filter { it.role == "user" }
                        .takeLast(6)
                        .map { it.content }
                    ProductCardList(
                        products = msg.products,
                        userQueries = recentQueries,
                        onProductClick = onProductClick,
                        onAddToCart = { item ->
                            val sku = item.skus.firstOrNull()
                            cartViewModel.addToCart(
                                CartAddRequest(
                                    product_id = item.product.product_id,
                                    sku_id = sku?.sku_id,
                                    title = item.product.title,
                                    brand = item.product.brand,
                                    image_path = item.product.image_path,
                                    unit_price = sku?.price ?: item.product.base_price
                                )
                            )
                        }
                    )
                }
            }
        }
    }

    // 已选中图片预览提示
    selectedImageUri?.let { uri ->
        AlertDialog(
            onDismissRequest = { selectedImageUri = null },
            title = { Text("已选择图片") },
            text = {
                AsyncImage(model = uri, contentDescription = null,
                    modifier = Modifier.fillMaxWidth().height(200.dp))
            },
            confirmButton = {
                TextButton(onClick = { }) {
                    Text("继续输入描述词后发送")
                }
            }
        )
    }

    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text("确认退出登录") },
            text = { Text("确定要退出当前账号吗？") },
            confirmButton = {
                TextButton(onClick = {
                    authViewModel.logout(onSuccess = onLogoutSuccess)
                    showLogoutDialog = false
                }) {
                    Text("确定退出")
                }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutDialog = false }) {
                    Text("取消")
                }
            }
        )
    }

    LaunchedEffect(uiState.messages.size) {
        if(uiState.messages.isNotEmpty()) {
            kotlinx.coroutines.delay(50)
            listState.scrollToItem(uiState.messages.size-1)
        }
    }
}

@Composable
fun ChatBubble(message: ChatMessage) {
    val isUser = message.role == "user"
    Box(modifier= Modifier.fillMaxWidth().padding(vertical=6.dp),
        contentAlignment = if(isUser) Alignment.CenterEnd else Alignment.CenterStart) {
        Surface(
            shape= RoundedCornerShape(topStart= if(isUser)20.dp else 4.dp, topEnd= if(isUser)4.dp else 20.dp, bottomStart=20.dp, bottomEnd=20.dp),
            color= if(isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondaryContainer,
            shadowElevation=2.dp, modifier= Modifier.widthIn(max=280.dp)
        ) {
            Column(Modifier.padding(14.dp)) {
                if(message.isStreaming && message.content.isEmpty()) {
                    TypingIndicator()
                } else {
                    Text(text=message.content, fontSize=15.sp,
                        lineHeight=22.sp,
                        color = if(isUser) Color.White else MaterialTheme.colorScheme.onSecondaryContainer)
                }
            }
        }
    }
}

@Composable
fun TypingIndicator() {
    val infiniteTransition = rememberInfiniteTransition()
    val offset1 by infiniteTransition.animateFloat(0f,1f,
        animationSpec = infiniteRepeatable(tween(700, 0, EaseInOut ), RepeatMode.Restart ))
    val offset2 by infiniteTransition.animateFloat(0f,1f,
        animationSpec = infiniteRepeatable(tween(700, 200, EaseInOut ), RepeatMode.Restart ))
    val offset3 by infiniteTransition.animateFloat(0f,1f,
        animationSpec = infiniteRepeatable(tween(700,400, EaseInOut ), RepeatMode.Restart ))
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Dot(if(offset1<0.5f) 0.6f else 1f)
        Dot(if(offset2<0.5f)0.6f else 1f)
        Dot(if(offset3<0.5f)0.6f else 1f)
    }
}
@Composable private fun Dot(alpha:Float) {
    Box(Modifier.size(8.dp).background(MaterialTheme.colorScheme.onSurface.copy(alpha=0.5f*alpha), CircleShape))
}

@Composable
fun ProductCardList(products: List<ProductItem>, userQueries: List<String>,
                    onProductClick: (String)->Unit, onAddToCart: (ProductItem)->Unit) {
    val target = remember(userQueries) { CategoryFilter.detectWithFallback(userQueries) }
    val safeList = remember(products, target) {
        if(target.category==null) products
        else {
            val filtered = if(target.subcategory!=null) products.filter { it.product.sub_category == target.subcategory }
            else products.filter { it.product.category == target.category }
            if(filtered.isNotEmpty()) filtered else products
        }
    }
    Column(Modifier.fillMaxWidth()) {
        Text("为您推荐 ${safeList.size} 款商品：", fontSize=12.sp, fontWeight=FontWeight.Bold,
            color= MaterialTheme.colorScheme.onSurface.copy(alpha=0.6f), modifier= Modifier.padding(4.dp))
        if(safeList.isNotEmpty()) {
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Spacer(Modifier.width(4.dp))
                safeList.forEach { ProductCard(it, { onProductClick(it.product.product_id) }, { onAddToCart(it) }) }
                Spacer(Modifier.width(4.dp))
            }
        }
    }
}

@Composable
fun ProductCard(item: ProductItem, onClick:()->Unit, onAddToCart:()->Unit) {
    val p = item.product
    val fullImagePath = remember(p.image_path) {
        if(p.image_path.isNullOrEmpty()) ""
        else "file:///android_asset/${p.image_path}"
    }
    Card(Modifier.width(170.dp).clickable(onClick=onClick),
        shape= RoundedCornerShape(16.dp), elevation= CardDefaults.cardElevation(4.dp)) {
        Column {
            Box(Modifier.height(160.dp)) {
                AsyncImage(model= fullImagePath, contentDescription=p.title,
                    modifier= Modifier.fillMaxSize(), contentScale= androidx.compose.ui.layout.ContentScale.Crop )
            }
            Column(Modifier.padding(10.dp)) {
                Text( p.brand, fontSize=12.sp, fontWeight=FontWeight.Bold,
                    maxLines=1, color= MaterialTheme.colorScheme.primary)
                Spacer(Modifier.height(2.dp))
                Text( p.title, fontSize=12.sp, maxLines=2, lineHeight=18.sp,
                    color= MaterialTheme.colorScheme.onSurface )
                Spacer(Modifier.height(6.dp))
                Text( "¥${p.base_price}", fontSize=17.sp, fontWeight=FontWeight.Bold,
                    color= MaterialTheme.colorScheme.error)
                Text("${item.skus.size}个规格可选", fontSize=11.sp,
                    color= MaterialTheme.colorScheme.onSurface.copy(alpha=0.5f))
                Spacer(Modifier.height(8.dp))
                Button(onClick=onAddToCart, Modifier.fillMaxWidth(),
                    contentPadding= PaddingValues(vertical=8.dp), shape= RoundedCornerShape(12.dp)) {
                    Text("加购物车", fontSize=13.sp)
                }
            }
        }
    }
}
