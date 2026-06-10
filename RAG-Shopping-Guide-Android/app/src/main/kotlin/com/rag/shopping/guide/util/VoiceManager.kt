package com.rag.shopping.guide.util

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.*
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

object VoiceManager {
    @Volatile
    private var tts: TextToSpeech? = null
    @Volatile
    private var isInitialized = false

    suspend fun init(context: Context): Boolean = suspendCoroutine { cont ->
        if (isInitialized && tts != null) {
            cont.resume(true)
            return@suspendCoroutine
        }
        
        try {
            tts = TextToSpeech(context) { status ->
                if (status == TextToSpeech.SUCCESS) {
                    try {
                        val result = tts?.setLanguage(Locale.SIMPLIFIED_CHINESE)
                        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                            tts?.language = Locale.CHINA
                        }
                        tts?.setPitch(1.0f)
                        tts?.setSpeechRate(1.0f)
                        isInitialized = true
                        cont.resume(true)
                    } catch (e: Exception) {
                        isInitialized = false
                        cont.resume(false)
                    }
                } else {
                    isInitialized = false
                    cont.resume(false)
                }
            }
        } catch (e: Exception) {
            isInitialized = false
            cont.resume(false)
        }
    }

    fun speak(text: String) {
        if (!isInitialized || tts == null || text.isBlank()) return
        try {
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "utterance_${System.currentTimeMillis()}")
        } catch (_: Exception) {}
    }

    fun stop() {
        try {
            tts?.stop()
        } catch (_: Exception) {}
    }

    fun isSpeaking(): Boolean {
        return try {
            tts?.isSpeaking == true
        } catch (_: Exception) {
            false
        }
    }

    fun shutdown() {
        try {
            tts?.stop()
            tts?.shutdown()
        } catch (_: Exception) {}
        isInitialized = false
        tts = null
    }
}
