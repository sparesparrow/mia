package cz.mia.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

private val MiaColorScheme = darkColorScheme(
    primary = MiaRed,
    onPrimary = MiaWhite,
    primaryContainer = Color(0xFF5C0017),
    onPrimaryContainer = MiaWhite,
    secondary = MiaCyan,
    onSecondary = Color(0xFF002020),
    secondaryContainer = Color(0xFF004D4D),
    onSecondaryContainer = MiaWhite,
    tertiary = MiaYellow,
    onTertiary = Color(0xFF1A1A00),
    tertiaryContainer = Color(0xFF4D4D00),
    onTertiaryContainer = MiaWhite,
    background = MiaBackground,
    onBackground = MiaWhite,
    surface = MiaSurface,
    onSurface = MiaWhite,
    surfaceVariant = MiaSurfaceVariant,
    onSurfaceVariant = MiaGrey,
    surfaceTint = MiaRed,
    outline = MiaOutline,
    outlineVariant = MiaOutline,
    error = MiaError,
    onError = Color(0xFF1A0000),
    errorContainer = Color(0xFF5C1111),
    onErrorContainer = MiaWhite,
    surfaceDim = MiaBackground,
    surfaceBright = MiaSurfaceVariant,
    surfaceContainerLowest = MiaBackground,
    surfaceContainerLow = MiaSurface,
    surfaceContainer = MiaSurface,
    surfaceContainerHigh = MiaSurfaceRaised,
    surfaceContainerHighest = MiaSurfaceRaised,
)

/** Colours the Material scheme has no slot for: success, warning and info. */
@Immutable
data class MiaExtraColors(
    val success: Color,
    val warning: Color,
    val info: Color,
)

private val DefaultExtras = MiaExtraColors(success = MiaSuccess, warning = MiaWarning, info = MiaInfo)

val LocalMiaColors = staticCompositionLocalOf { DefaultExtras }

/** `MaterialTheme.mia.warning` and friends. */
val MaterialTheme.mia: MiaExtraColors
    @Composable
    @ReadOnlyComposable
    get() = LocalMiaColors.current

/** The app theme. Dark whatever the system setting is: there is no light scheme. */
@Composable
fun MiaTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalMiaColors provides DefaultExtras) {
        MaterialTheme(
            colorScheme = MiaColorScheme,
            typography = MiaTypography,
            content = content,
        )
    }
}
