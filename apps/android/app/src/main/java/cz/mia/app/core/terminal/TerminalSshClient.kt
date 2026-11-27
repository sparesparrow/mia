package cz.mia.app.core.terminal

import com.hierynomus.sshj.key.KeyAlgorithms
import java.security.Security
import net.schmizz.sshj.DefaultConfig
import net.schmizz.sshj.SSHClient
import org.bouncycastle.jce.provider.BouncyCastleProvider

/**
 * The key algorithms the terminal's client offers (REQ-AND-029). sshj uses this one list both to negotiate the host
 * key and to sign the user's key, so it must hold ecdsa-sha2-nistp256 for the phone's EC P-256 terminal key;
 * ed25519 comes first, so a Pi with an ed25519 host key always presents that one, and [TerminalHostKeys] refuses
 * any other host key type anyway.
 */
val TERMINAL_KEY_ALGORITHMS: List<String> = listOf("ssh-ed25519", "ecdsa-sha2-nistp256")

/** An SSH client for the terminal: ed25519 host keys first, and the phone's ECDSA P-256 key for sign-in. */
fun newTerminalSshClient(): SSHClient {
	// sshj needs the full BouncyCastle, not the cut-down copy Android ships under the same name.
	Security.removeProvider("BC")
	Security.insertProviderAt(BouncyCastleProvider(), 1)
	val config = DefaultConfig()
	config.keyAlgorithms = listOf(KeyAlgorithms.EdDSA25519(), KeyAlgorithms.ECDSASHANistp256())
	check(config.keyAlgorithms.map { it.name } == TERMINAL_KEY_ALGORITHMS)
	return SSHClient(config)
}
