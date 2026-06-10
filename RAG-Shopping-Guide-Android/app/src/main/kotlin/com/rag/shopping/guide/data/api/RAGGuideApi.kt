// Retrofit API 服务接口
package com.rag.shopping.guide.data.api

import com.rag.shopping.guide.data.model.*
import okhttp3.MultipartBody
import retrofit2.http.*

interface RAGGuideApi {
    
    @GET("health")
    suspend fun healthCheck(): Map<String, String>
    
    @POST("api/v1/chat")
    suspend fun chat(@Body request: ChatRequest): ChatResponse
    
    @POST("api/v1/search")
    suspend fun search(@Body request: SearchRequest): SearchResponse
    
    @Multipart
    @POST("api/v1/search/image")
    suspend fun searchByImage(
        @Part image: MultipartBody.Part,
        @Part("query") query: String? = null
    ): SearchResponse
    
    @GET("api/v1/product/{product_id}")
    suspend fun getProduct(@Path("product_id") productId: String): com.rag.shopping.guide.data.model.GetProductResponse

    // ========== 登录注册 ==========
    @POST("api/v1/auth/register")
    suspend fun register(@Body request: AuthRequest): AuthResponse
    
    @POST("api/v1/auth/login")
    suspend fun login(@Body request: AuthRequest): AuthResponse
    
    @POST("api/v1/auth/logout")
    suspend fun logout(): Map<String, Any>
    
    @GET("api/v1/auth/me")
    suspend fun me(): MeResponse

    // ========== 购物车相关API (已用AuthInterceptor自动注入Bearer header，不需要user_id参数) ==========
    @POST("api/v1/cart")
    suspend fun addToCart(@Body request: CartAddRequest): Map<String, Any>

    @GET("api/v1/cart")
    suspend fun getCart(): CartResponse

    @PUT("api/v1/cart/{item_id}")
    suspend fun updateCartItem(
        @Path("item_id") itemId: Int,
        @Body request: CartUpdateRequest
    ): Map<String, Any>

    @DELETE("api/v1/cart/{item_id}")
    suspend fun removeCartItem(@Path("item_id") itemId: Int): Map<String, Any>

    @DELETE("api/v1/cart")
    suspend fun clearCart(): Map<String, Any>
}
