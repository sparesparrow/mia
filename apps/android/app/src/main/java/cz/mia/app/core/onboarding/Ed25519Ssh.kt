package cz.mia.app.core.onboarding

import com.hierynomus.sshj.key.KeyAlgorithms
import java.security.Security
import net.schmizz.sshj.DefaultConfig
import net.schmizz.sshj.SSHClient
import org.bouncycastle.jce.provider.BouncyCastleProvider

/**
 * The one place that builds an SSH client for talking to a Pi whose host key is pinned (REQ-ONB-008): only
 * ssh-ed25519 is offered as host-key algorithm, so a Pi without that key fails negotiation instead of presenting a key
 * the pin check cannot compare. Used by the host-key reader, the enroll step and the install upload.
 */
fun newEd25519SshClient(): SSHClient {
	// sshj needs the full BouncyCastle, not the cut-down copy Android ships under the same name.
	Security.removeProvider("BC")
	Security.insertProviderAt(BouncyCastleProvider(), 1)
	val config = DefaultConfig()
	config.keyAlgorithms = listOf(KeyAlgorithms.EdDSA25519())
	return SSHClient(config)
}
