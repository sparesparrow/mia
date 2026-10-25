package cz.mia.app.core.voice

import cz.mia.app.core.background.AlertSeverity
import cz.mia.app.core.background.VehicleAlert
import cz.mia.app.core.rules.CarWarningCodes
import cz.mia.app.core.rules.CarWarningTexts

data class SpokenWarning(
    val code: String,
    val text: String,
    val priority: SpeechPriority,
    val interrupt: Boolean,
)

/**
 * Decides when a car warning may be spoken. It never transmits on a vehicle bus.
 * A missing signal is unknown, not a clearance.
 */
class SpokenCarWarnings(
    private val coolantCriticalC: Double = 105.0,
    private val batteryLowV: Double = 11.5,
    private val criticalRepeatMs: Long = 60_000L,
    private val warningRepeatMs: Long = 300_000L,
) {
    private val latched = mutableSetOf<String>()
    private val lastSpokenAt = mutableMapOf<String, Long>()

    fun gate(active: List<VehicleAlert>, nowMs: Long): List<SpokenWarning> {
        return gateKnown(active, active.map { it.code }.toSet(), nowMs)
    }

    fun cycle1(coolantC: Double?, batteryV: Double?, nowMs: Long): List<SpokenWarning> {
        val active = mutableListOf<VehicleAlert>()
        val known = mutableSetOf<String>()
        if (coolantC != null) {
            known += CarWarningCodes.ENGINE_OVERHEAT
            if (coolantC > coolantCriticalC) active += overheat()
        }
        if (batteryV != null) {
            known += CarWarningCodes.BATTERY_LOW
            if (batteryV < batteryLowV) active += battery()
        }
        return gateKnown(active, known, nowMs)
    }

    private fun gateKnown(
        active: List<VehicleAlert>,
        knownCodes: Set<String>,
        nowMs: Long,
    ): List<SpokenWarning> {
        knownCodes
            .filter { code -> active.none { it.code == code } }
            .forEach { code ->
                latched.remove(code)
                lastSpokenAt.remove(code)
            }
        return active.mapNotNull { speakIfDue(it, nowMs) }
    }

    private fun speakIfDue(alert: VehicleAlert, nowMs: Long): SpokenWarning? {
        val repeatAfter = if (alert.severity == AlertSeverity.CRITICAL) {
            criticalRepeatMs
        } else {
            warningRepeatMs
        }
        val spokenAt = lastSpokenAt[alert.code]
        val due = alert.code !in latched || spokenAt == null || nowMs - spokenAt >= repeatAfter
        if (!due) return null
        latched += alert.code
        lastSpokenAt[alert.code] = nowMs
        val critical = alert.severity == AlertSeverity.CRITICAL
        return SpokenWarning(
            code = alert.code,
            text = alert.message,
            priority = if (critical) SpeechPriority.CRITICAL else SpeechPriority.HIGH,
            interrupt = critical,
        )
    }

    private fun overheat() = VehicleAlert(
        severity = AlertSeverity.CRITICAL,
        code = CarWarningCodes.ENGINE_OVERHEAT,
        message = CarWarningTexts.ENGINE_OVERHEAT,
    )

    private fun battery() = VehicleAlert(
        severity = AlertSeverity.WARNING,
        code = CarWarningCodes.BATTERY_LOW,
        message = CarWarningTexts.BATTERY_LOW,
    )
}
