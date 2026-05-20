# Keep codec classes — JSON map uses class structure
-keep class com.cccstudios.newmx.codec.** { *; }

# Standard Android stuff
-keep class com.cccstudios.newmx.MainActivity { *; }
-keep class com.cccstudios.newmx.ProcessTextActivity { *; }
-keep class com.cccstudios.newmx.EncodeShareActivity { *; }

# Kotlin metadata
-keep class kotlin.Metadata { *; }
