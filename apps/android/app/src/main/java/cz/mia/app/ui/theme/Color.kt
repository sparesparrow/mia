package cz.mia.app.ui.theme

import androidx.compose.ui.graphics.Color

/** Gonzo neon palette. Dark first: the car is used at night and the app has no light mode. */
val MiaBackground = Color(0xFF0A0A0A)
val MiaSurface = Color(0xFF1A0A1A)
val MiaSurfaceRaised = Color(0xFF241224)
val MiaSurfaceVariant = Color(0xFF2E1F2E)
val MiaOutline = Color(0xFF333333)

val MiaRed = Color(0xFFFF0040)
val MiaCyan = Color(0xFF00FFFF)
val MiaYellow = Color(0xFFFFFF00)
val MiaWhite = Color(0xFFFFFFFF)
val MiaGrey = Color(0xFFCCCCCC)

/**
 * Red is the brand colour, so it cannot also be the only sign of an error. Errors use this lighter red
 * and always come with an icon or a word as well (see ErrorLabel in the components).
 */
val MiaError = Color(0xFFFF4444)
val MiaSuccess = Color(0xFF39FF14)
val MiaWarning = Color(0xFFFFFF00)
val MiaInfo = Color(0xFF00FFFF)
