# Правила ProGuard/R8 для release-сборки.
# Приложение не использует reflection и сторонних библиотек,
# поэтому дополнительных keep-правил не требуется.
-keepattributes SourceFile,LineNumberTable
