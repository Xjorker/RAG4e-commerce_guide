// Retrofit 客户端单例 - 支持真机+模拟器双模式
package com.rag.shopping.guide.data.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    
    // 本地模式：Android模拟器专属地址 10.0.2.2 映射到电脑本机 9000
    private const val BASE_URL = "http://10.0.2.2:9000/"
    
    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }
    
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(120, TimeUnit.SECONDS)
        .readTimeout(180, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .addInterceptor(AuthInterceptor())
        .addInterceptor(logging)
        .build()
    
    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    val api: RAGGuideApi by lazy {
        retrofit.create(RAGGuideApi::class.java)
    }
}
