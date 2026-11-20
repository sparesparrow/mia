package cz.mia.app.core.onboarding

/** A Pi the wizard finished onboarding: its SSH host-key fingerprint (`SHA256:<base64>`) and the host it answered on. */
data class KnownPi(val fp: String, val host: String)

/** Where [KnownPiStore] keeps its lines; a SharedPreferences adapter in production, a fake in JVM tests. */
interface KnownPiStorage {
	fun read(): Set<String>
	fun write(lines: Set<String>)
}

/**
 * Pis that completed the whole wizard. [OnboardingMachine] saves only when it reaches Done, never after a failed step.
 * One entry per fingerprint; saving again updates the host.
 */
class KnownPiStore(private val storage: KnownPiStorage) {
	@Synchronized
	fun save(fp: String, host: String) {
		require(fp.isNotEmpty() && host.isNotEmpty() && ' ' !in fp) { "fingerprint and host are required" }
		val kept = storage.read().filter { it.substringBefore(' ') != fp }
		storage.write((kept + "$fp $host").toSet())
	}

	@Synchronized
	fun known(): List<KnownPi> =
		storage.read().sorted().mapNotNull { line ->
			val fp = line.substringBefore(' ')
			val host = line.substringAfter(' ', "")
			if (fp.isEmpty() || host.isEmpty()) null else KnownPi(fp, host)
		}
}
