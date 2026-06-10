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

    // 购物车相关API
    @POST("api/v1/cart")
    suspend fun addToCart(@Body request: CartAddRequest): Map<String, Any>

    @GET("api/v1/cart")
    suspend fun getCart(@Query("user_id") userId: String): CartResponse

    @PUT("api/v1/cart/{item_id}")
    suspend fun updateCartItem(
        @Path("item_id") itemId: Int,
        @Body request: CartUpdateRequest
    ): Map<String, Any>

    @DELETE("api/v1/cart/{item_id}")
    suspend fun removeCartItem(@Path("item_id") itemId: Int): Map<String, Any>

    @DELETE("api/v1/cart")
    suspend fun clearCart(@Query("user_id") userId: String): Map<String, Any>
}
