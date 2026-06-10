// SSE流式客户端 - 通过OkHttp直接处理Server-Sent Events
package com.rag.shopping.guide.data.api

import com.google.gson.Gson
import com.rag.shopping.guide.data.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.flowOn
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.concurrent.TimeUnit

class SSEClient(private val baseUrl: String) {
    
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(180, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()
    
    fun streamChat(request: ChatRequest): Flow<SSEEvent> = callbackFlow {
        val url = "${baseUrl.trimEnd('/')}/api/v1/chat/stream"
        val jsonBody = gson.toJson(request)
        
        val req = Request.Builder()
            .url(url)
            .addHeader("Content-Type", "application/json")
            .addHeader("Accept", "text/event-stream")
            .post(jsonBody.toRequestBody("application/json".toMediaType()))
            .build()
        
        val call = client.newCall(req)
        
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, e: java.io.IOException) {
                trySend(SSEEvent.Error("Network error: ${e.message}"))
                close(e)
            }
            
            override fun onResponse(call: Call, response: Response) {
                if (!response.isSuccessful) {
                    trySend(SSEEvent.Error("HTTP ${response.code}"))
                    close()
                    return
                }
                
                val inputStream = response.body?.byteStream() ?: run {
                    trySend(SSEEvent.Error("No response body"))
                    close()
                    return
                }
                
                val reader = BufferedReader(InputStreamReader(inputStream, Charsets.UTF_8))
                
                try {
                    var currentEvent = ""
                    var currentData = ""
                    
                    while (true) {
                        val line = reader.readLine() ?: break
                        if (line.isEmpty()) {
                            if (currentData.isNotEmpty()) {
                                val event = parseSSEData(currentData)
                                if (event != null) {
                                    trySend(event)
                                }
                            }
                            currentEvent = ""
                            currentData = ""
                            continue
                        }
                        if (line.startsWith("event:")) {
                            currentEvent = line.substring(6).trim()
                        } else if (line.startsWith("data:")) {
                            currentData = line.substring(5).trim()
                        }
                    }
                } catch (e: Exception) {
                    trySend(SSEEvent.Error("Stream error: ${e.message}"))
                } finally {
                    close()
                }
            }
        })
        
        awaitClose { call.cancel() }
    }.flowOn(Dispatchers.IO)
    
    private fun parseSSEData(data: String): SSEEvent? {
        return try {
            val json = gson.fromJson(data, com.google.gson.JsonObject::class.java)
            
            when {
                json.has("type") -> {
                    when (val type = json.get("type").asString) {
                        "session" -> SSEEvent.Session(json.get("session_id").asString)
                        "content" -> SSEEvent.Content(json.get("delta").asString)
                        "done" -> SSEEvent.Done(json.get("session_id").asString)
                        "error" -> SSEEvent.Error(json.get("message").asString)
                        "products" -> {
                            val productsArray = json.getAsJsonArray("products")
                            val products = mutableListOf<ProductItem>()
                            for (elem in productsArray) {
                                val obj = elem.asJsonObject
                                val product = gson.fromJson(obj.get("product"), Product::class.java)
                                val skusArray = obj.getAsJsonArray("skus")
                                val skus = mutableListOf<Sku>()
                                for (s in skusArray) {
                                    skus.add(gson.fromJson(s, Sku::class.java))
                                }
                                products.add(ProductItem(product, skus))
                            }
                            SSEEvent.Products(products)
                        }
                        else -> null
                    }
                }
                else -> null
            }
        } catch (e: Exception) {
            null
        }
    }
}

object SSEClientFactory {
    fun create(baseUrl: String): SSEClient = SSEClient(baseUrl)
}
