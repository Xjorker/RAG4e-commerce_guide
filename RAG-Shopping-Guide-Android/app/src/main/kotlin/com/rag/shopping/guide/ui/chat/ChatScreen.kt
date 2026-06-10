// Main Chat Screen UI - 支持SSE流式 + 打字指示器 + 100% 后端原始顺序
package com.rag.shopping.guide.ui.chat

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
import androidx.compose.material3.*
import androidx.compose.runtime.*
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
    viewModel: ChatViewModel = viewModel(),
    cartViewModel: CartViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val cart by cartViewModel.cart.collectAsState(initial = CartResponse(emptyList(),0,0.0))
    val listState = rememberLazyListState()
    var inputText by remember { mutableStateOf(TextFieldValue("")) }

    LaunchedEffect(Unit) { cartViewModel.loadCart() }

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
                }
            )
        },
        bottomBar = {
            Surface(modifier = Modifier.navigationBarsPadding().imePadding(), shadowElevation=8.dp) {
                Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconButton({}) {
                        Icon(Icons.Default.AttachFile, null, tint = MaterialTheme.colorScheme.primary)
                    }
                    OutlinedTextField(inputText, {inputText=it}, Modifier.weight(1f),
                        placeholder={Text("请输入您的问题")}, maxLines=3, shape= RoundedCornerShape(24.dp))
                    Spacer(Modifier.width(8.dp))
                    IconButton({
                        if(inputText.text.isNotBlank()) {
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
                // ✅ 核心改动：如果这条消息是助手返回，并且它自己带了 products 卡片，直接紧接在这条消息下面渲染
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
    LaunchedEffect(uiState.messages.size) {
        if(uiState.messages.isNotEmpty()) {
            delay(50)
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
                    // Typing 三个点动画 - AI 正在思考
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
        animationSpec = infiniteRepeatable( tween(700, 0, EaseInOut ), RepeatMode.Restart ))
    val offset2 by infiniteTransition.animateFloat(0f,1f,
        animationSpec = infiniteRepeatable( tween(700, 200, EaseInOut ), RepeatMode.Restart ))
    val offset3 by infiniteTransition.animateFloat(0f,1f,
        animationSpec = infiniteRepeatable( tween(700,400, EaseInOut ), RepeatMode.Restart ))
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
    // 完全信任后端返回顺序！不做任何 sort，100% 保证文字和卡片顺序一致
    val target = remember(userQueries) { CategoryFilter.detectWithFallback(userQueries) }
    // 仅做基础子品类过滤防御，顺序完全保留后端原始顺序
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
            color=MaterialTheme.colorScheme.onSurface.copy(alpha=0.6f), modifier= Modifier.padding(4.dp))
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
    // 完全复用详情页的图片加载方式！本地Android Assets，不走后端网络！
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
