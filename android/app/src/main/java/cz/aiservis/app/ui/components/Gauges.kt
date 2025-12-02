package cz.aiservis.app.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocalGasStation
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Thermostat
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import cz.aiservis.app.data.db.TelemetryEntity
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Enhanced Dashboard Gauges with speedometer, RPM, and other indicators.
 */
@Composable
fun DashboardGauges(latest: TelemetryEntity?) {
    if (latest == null) {
        NoTelemetryPlaceholder()
        return
    }
    
    Column(modifier = Modifier.fillMaxWidth()) {
        // Main gauges row (Speedometer & RPM)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            SpeedometerGauge(
                value = latest.vehicleSpeed,
                maxValue = 200,
                modifier = Modifier.weight(1f)
            )
            
            Spacer(Modifier.width(8.dp))
            
            RPMGauge(
                value = latest.engineRpm,
                maxValue = 8000,
                modifier = Modifier.weight(1f)
            )
        }
        
        Spacer(Modifier.height(16.dp))
        
        // Secondary indicators row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            CompactGauge(
                label = "Fuel",
                value = latest.fuelLevel,
                maxValue = 100,
                unit = "%",
                icon = Icons.Default.LocalGasStation,
                warningThreshold = 20,
                modifier = Modifier.weight(1f)
            )
            
            Spacer(Modifier.width(8.dp))
            
            CompactGauge(
                label = "Coolant",
                value = latest.coolantTemp,
                maxValue = 120,
                unit = "°C",
                icon = Icons.Default.Thermostat,
                warningThreshold = 100,
                isWarningAbove = true,
                modifier = Modifier.weight(1f)
            )
            
            Spacer(Modifier.width(8.dp))
            
            CompactGauge(
                label = "Load",
                value = latest.engineLoad,
                maxValue = 100,
                unit = "%",
                icon = Icons.Default.Speed,
                warningThreshold = 90,
                isWarningAbove = true,
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun NoTelemetryPlaceholder() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Default.Speed,
                contentDescription = null,
                modifier = Modifier.size(48.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = "No telemetry data",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = "Connect to OBD adapter to view vehicle data",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
            )
        }
    }
}

/**
 * Circular speedometer gauge with needle.
 */
@Composable
fun SpeedometerGauge(
    value: Int,
    maxValue: Int,
    modifier: Modifier = Modifier
) {
    val animatedValue by animateFloatAsState(
        targetValue = value.toFloat(),
        animationSpec = tween(durationMillis = 500),
        label = "speedometer"
    )
    
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f),
                contentAlignment = Alignment.Center
            ) {
                CircularGauge(
                    value = animatedValue,
                    maxValue = maxValue.toFloat(),
                    arcColor = when {
                        value > 160 -> Color(0xFFF44336) // Red for high speed
                        value > 120 -> Color(0xFFFFC107) // Yellow for moderate
                        else -> Color(0xFF4CAF50) // Green for normal
                    }
                )
                
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = value.toString(),
                        fontSize = 36.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = "km/h",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            
            Spacer(Modifier.height(4.dp))
            
            Text(
                text = "Speed",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * RPM gauge with tachometer-style display.
 */
@Composable
fun RPMGauge(
    value: Int,
    maxValue: Int,
    modifier: Modifier = Modifier
) {
    val animatedValue by animateFloatAsState(
        targetValue = value.toFloat(),
        animationSpec = tween(durationMillis = 500),
        label = "rpm"
    )
    
    val redlineRpm = (maxValue * 0.85).toInt()
    
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f),
                contentAlignment = Alignment.Center
            ) {
                CircularGauge(
                    value = animatedValue,
                    maxValue = maxValue.toFloat(),
                    arcColor = when {
                        value >= redlineRpm -> Color(0xFFF44336) // Redline
                        value >= maxValue * 0.7 -> Color(0xFFFFC107) // Yellow zone
                        else -> Color(0xFF2196F3) // Normal blue
                    },
                    hasRedzone = true,
                    redzoneStart = redlineRpm.toFloat() / maxValue
                )
                
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = (value / 100).toString(),
                        fontSize = 36.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = "x100",
                        fontSize = 10.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            
            Spacer(Modifier.height(4.dp))
            
            Text(
                text = "RPM",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * Circular gauge arc with optional redzone.
 */
@Composable
private fun CircularGauge(
    value: Float,
    maxValue: Float,
    arcColor: Color,
    hasRedzone: Boolean = false,
    redzoneStart: Float = 0.85f
) {
    val progress = (value / maxValue).coerceIn(0f, 1f)
    val backgroundColor = MaterialTheme.colorScheme.surfaceVariant
    
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .padding(8.dp)
    ) {
        val strokeWidth = size.width * 0.08f
        val diameter = size.width - strokeWidth
        val startAngle = 135f
        val sweepAngle = 270f
        
        // Background arc
        drawArc(
            color = backgroundColor,
            startAngle = startAngle,
            sweepAngle = sweepAngle,
            useCenter = false,
            topLeft = Offset(strokeWidth / 2, strokeWidth / 2),
            size = Size(diameter, diameter),
            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
        )
        
        // Redzone arc (if enabled)
        if (hasRedzone) {
            drawArc(
                color = Color(0xFFF44336).copy(alpha = 0.3f),
                startAngle = startAngle + sweepAngle * redzoneStart,
                sweepAngle = sweepAngle * (1f - redzoneStart),
                useCenter = false,
                topLeft = Offset(strokeWidth / 2, strokeWidth / 2),
                size = Size(diameter, diameter),
                style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
            )
        }
        
        // Value arc
        drawArc(
            color = arcColor,
            startAngle = startAngle,
            sweepAngle = sweepAngle * progress,
            useCenter = false,
            topLeft = Offset(strokeWidth / 2, strokeWidth / 2),
            size = Size(diameter, diameter),
            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
        )
        
        // Needle indicator
        val needleAngle = startAngle + sweepAngle * progress
        val needleRadians = needleAngle * PI / 180
        val needleLength = diameter / 2 - strokeWidth
        val centerX = size.width / 2
        val centerY = size.height / 2
        val needleX = centerX + needleLength * cos(needleRadians).toFloat()
        val needleY = centerY + needleLength * sin(needleRadians).toFloat()
        
        drawLine(
            color = arcColor,
            start = Offset(centerX, centerY),
            end = Offset(needleX, needleY),
            strokeWidth = strokeWidth * 0.3f,
            cap = StrokeCap.Round
        )
        
        // Center dot
        drawCircle(
            color = arcColor,
            radius = strokeWidth * 0.4f,
            center = Offset(centerX, centerY)
        )
    }
}

/**
 * Compact linear gauge for secondary indicators.
 */
@Composable
fun CompactGauge(
    label: String,
    value: Int,
    maxValue: Int,
    unit: String,
    icon: ImageVector,
    warningThreshold: Int,
    isWarningAbove: Boolean = false,
    modifier: Modifier = Modifier
) {
    val animatedProgress by animateFloatAsState(
        targetValue = (value.toFloat() / maxValue).coerceIn(0f, 1f),
        animationSpec = tween(durationMillis = 500),
        label = "compactGauge"
    )
    
    val isWarning = if (isWarningAbove) value >= warningThreshold else value <= warningThreshold
    val gaugeColor = if (isWarning) Color(0xFFF44336) else MaterialTheme.colorScheme.primary
    
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Icon(
                    imageVector = if (isWarning) Icons.Default.Warning else icon,
                    contentDescription = null,
                    tint = gaugeColor,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            Spacer(Modifier.height(8.dp))
            
            Text(
                text = "$value$unit",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = gaugeColor
            )
            
            Spacer(Modifier.height(8.dp))
            
            LinearProgressIndicator(
                progress = { animatedProgress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = gaugeColor,
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )
        }
    }
}

/**
 * Simple linear gauge for basic indicators (legacy support).
 */
@Composable
private fun Gauge(label: String, value: Int, max: Int) {
    val animatedProgress by animateFloatAsState(
        targetValue = (value.toFloat() / max).coerceIn(0f, 1f),
        animationSpec = tween(durationMillis = 500),
        label = "gauge"
    )
    
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium
            )
            Text(
                text = "$value / $max",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = { animatedProgress },
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(RoundedCornerShape(4.dp))
        )
    }
}
