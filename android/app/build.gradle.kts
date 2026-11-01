plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Настройки сборки приходят из config/android-build.json через -P…:
// имя приложения, package id, версия и адрес шлюза по умолчанию.
fun buildProp(name: String, fallback: String): String =
    (project.findProperty(name) as String?)?.takeIf { it.isNotBlank() } ?: fallback

val appName = buildProp("appName", "RUD Panel")
val appId = buildProp("appId", "com.rudpanel.gateway")
val appVersionName = buildProp("appVersionName", "0.1.0")
val appVersionCode = buildProp("appVersionCode", "1").toIntOrNull() ?: 1
val defaultHost = buildProp("defaultHost", "")
val defaultPort = buildProp("defaultPort", "8760").toIntOrNull() ?: 8760

android {
    namespace = "com.rudpanel.gateway"
    compileSdk = 35

    defaultConfig {
        applicationId = appId
        minSdk = 26
        targetSdk = 35
        versionCode = appVersionCode
        versionName = appVersionName
        manifestPlaceholders["appName"] = appName
        buildConfigField("String", "DEFAULT_HOST", "\"$defaultHost\"")
        buildConfigField("int", "DEFAULT_PORT", "$defaultPort")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    // Намеренно пусто: только Android SDK и Kotlin stdlib.
    // Это упрощает offline-сборку и уменьшает APK.
}
