// RAG智能导购 Android Application Class
package com.rag.shopping.guide

import android.app.Application

class RAGGuideApp : Application() {
    
    companion object {
        lateinit var instance: RAGGuideApp
            private set
    }
    
    override fun onCreate() {
        super.onCreate()
        instance = this
    }
}
