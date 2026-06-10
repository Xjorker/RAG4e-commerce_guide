package com.rag.shopping.guide.ui.chat

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.content.pm.ResolveInfo
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MicNone
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.delay
import java.util.Locale

@Composable
fun VoiceInputButton(
    onTextRecognized: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var isRecording by remember { mutableStateOf(false) }
    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED
        )
    }
    
    // 安全检查：设备是否有语音识别服务
    var hasVoiceRecognitionFeature by remember {
        mutableStateOf(false)
    }
    
    LaunchedEffect(Unit) {
        try {
            val testIntent = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            val activities: List<ResolveInfo>? = context.packageManager.queryIntentActivities(testIntent, 0)
            hasVoiceRecognitionFeature = !activities.isNullOrEmpty()
        } catch (e: Exception) {
            hasVoiceRecognitionFeature = false
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasPermission = granted
        if (!granted) {
            android.widget.Toast.makeText(context, "需要录音权限才能使用语音输入", android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    val speechRecognizer = remember {
        try {
            SpeechRecognizer.createSpeechRecognizer(context)
        } catch (e: Exception) {
            null
        }
    }
    
    val listeningAnim by rememberInfiniteTransition().animateFloat(
        initialValue = 0.7f,
        targetValue = 1.3f,
        animationSpec = infiniteRepeatable(
            tween(800, 0, EaseInOut),
            RepeatMode.Reverse
        )
    )

    // 安全地设置监听器
    LaunchedEffect(Unit) {
        if (speechRecognizer != null) {
            val intent = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.SIMPLIFIED_CHINESE)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            }

            speechRecognizer.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: android.os.Bundle?) {
                    isRecording = true
                }

                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {
                    isRecording = false
                }

                override fun onError(error: Int) {
                    isRecording = false
                    val errorMsg = when (error) {
                        SpeechRecognizer.ERROR_AUDIO -> "音频错误"
                        SpeechRecognizer.ERROR_NO_MATCH -> "没听清，请再说一遍"
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "没有录音权限"
                        else -> "语音识别错误"
                    }
                    android.widget.Toast.makeText(context, errorMsg, android.widget.Toast.LENGTH_SHORT).show()
                }

                override fun onResults(results: android.os.Bundle?) {
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!matches.isNullOrEmpty()) {
                        val finalText = matches[0]
                        onTextRecognized(finalText)
                    }
                    isRecording = false
                }

                override fun onPartialResults(partialResults: android.os.Bundle?) {
                    val partial = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!partial.isNullOrEmpty()) {
                        onTextRecognized(partial[0])
                    }
                }

                override fun onEvent(eventType: Int, params: android.os.Bundle?) {}
            })
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            try {
                speechRecognizer?.cancel()
                speechRecognizer?.destroy()
            } catch (_: Exception) {}
        }
    }

    // 如果设备没有语音识别服务，显示一个不可点击的灰图标
    if (!hasVoiceRecognitionFeature) {
        Box(modifier = modifier.size(48.dp), contentAlignment = Alignment.Center) {
            Icon(
                imageVector = Icons.Default.MicNone,
                contentDescription = "语音输入（设备不支持）",
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f),
                modifier = Modifier.size(28.dp)
            )
        }
        return
    }

    Box(modifier = modifier.size(48.dp), contentAlignment = Alignment.Center) {
        if (isRecording) {
            Box(
                Modifier
                    .size(48.dp)
                    .scale(listeningAnim)
                    .background(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.3f),
                        CircleShape
                    )
            )
        }

        IconButton(
            onClick = {
                if (!hasPermission) {
                    permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                } else if (speechRecognizer == null) {
                    android.widget.Toast.makeText(context, "语音识别初始化失败，请重启App", android.widget.Toast.LENGTH_SHORT).show()
                } else {
                    try {
                        if (isRecording) {
                            speechRecognizer.stopListening()
                        } else {
                            val intent = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.SIMPLIFIED_CHINESE)
                                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                            }
                            speechRecognizer.startListening(intent)
                        }
                    } catch (e: Exception) {
                        android.widget.Toast.makeText(context, "启动语音识别出错: ${e.message}", android.widget.Toast.LENGTH_SHORT).show()
                    }
                }
            }
        ) {
            Icon(
                imageVector = if (isRecording) Icons.Default.Mic else Icons.Default.MicNone,
                contentDescription = "语音输入",
                tint = if (isRecording) Color.Red else MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(28.dp)
            )
        }
    }
}
