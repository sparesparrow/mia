package cz.mia.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import cz.mia.app.R

/** Bebas Neue (SIL OFL) for headings and titles. It has one weight. */
val BebasNeue = FontFamily(Font(R.font.bebas_neue_regular, FontWeight.Normal))

/**
 * JetBrains Mono (SIL OFL) for numeric readouts. The file is a variable font; the weight axis is applied from
 * Android 8, older versions draw its default weight.
 */
@OptIn(ExperimentalTextApi::class)
val MiaMono = FontFamily(
    Font(
        R.font.jetbrains_mono,
        FontWeight.Normal,
        variationSettings = FontVariation.Settings(FontVariation.weight(400)),
    ),
    Font(
        R.font.jetbrains_mono,
        FontWeight.Bold,
        variationSettings = FontVariation.Settings(FontVariation.weight(700)),
    ),
)

private val base = Typography()

val MiaTypography = Typography(
    displayLarge = base.displayLarge.copy(fontFamily = BebasNeue),
    displayMedium = base.displayMedium.copy(fontFamily = BebasNeue),
    displaySmall = base.displaySmall.copy(fontFamily = BebasNeue),
    headlineLarge = base.headlineLarge.copy(fontFamily = BebasNeue, letterSpacing = 1.sp),
    headlineMedium = base.headlineMedium.copy(fontFamily = BebasNeue, letterSpacing = 1.sp),
    headlineSmall = base.headlineSmall.copy(fontFamily = BebasNeue, letterSpacing = 1.sp),
    titleLarge = base.titleLarge.copy(fontFamily = BebasNeue, letterSpacing = 0.8.sp),
    titleMedium = base.titleMedium.copy(fontFamily = BebasNeue, fontWeight = FontWeight.Normal, letterSpacing = 0.8.sp),
    titleSmall = base.titleSmall.copy(fontFamily = BebasNeue, fontWeight = FontWeight.Normal, letterSpacing = 0.8.sp),
)

/** A numeric readout style: monospaced so digits do not jitter as they change. */
val MiaReadout = TextStyle(fontFamily = MiaMono, fontWeight = FontWeight.Bold)
