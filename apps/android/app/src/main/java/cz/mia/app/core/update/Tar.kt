package cz.mia.app.core.update

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.util.zip.GZIPInputStream

/** Just enough tar (ustar, regular files, names up to 100 bytes) to make a `.miapkg` and to read a release bundle. */
object Tar {
	private const val BLOCK = 512

	fun write(entries: List<Pair<String, ByteArray>>): ByteArray {
		val out = ByteArrayOutputStream()
		for ((name, data) in entries) {
			val nameBytes = name.toByteArray(Charsets.UTF_8)
			require(nameBytes.size <= 100) { "tar name too long: $name" }
			val header = ByteArray(BLOCK)
			nameBytes.copyInto(header)
			put(header, 100, "0000644\u0000")
			put(header, 108, "0000000\u0000")
			put(header, 116, "0000000\u0000")
			put(header, 124, "%011o\u0000".format(data.size))
			put(header, 136, "%011o\u0000".format(0))
			for (i in 148 until 156) header[i] = ' '.code.toByte()
			header[156] = '0'.code.toByte()
			put(header, 257, "ustar\u000000")
			val sum = header.sumOf { it.toInt() and 0xff }
			put(header, 148, "%06o\u0000 ".format(sum))
			out.write(header)
			out.write(data)
			out.write(ByteArray((BLOCK - data.size % BLOCK) % BLOCK))
		}
		out.write(ByteArray(BLOCK * 2))
		return out.toByteArray()
	}

	/** The regular files of a .tar.gz, by name; [wanted] filters names so a large bundle is not held whole in memory. */
	fun readGz(gz: ByteArray, wanted: (String) -> Boolean): Map<String, ByteArray> =
		read(GZIPInputStream(ByteArrayInputStream(gz)), wanted)

	fun read(input: InputStream, wanted: (String) -> Boolean): Map<String, ByteArray> {
		val found = linkedMapOf<String, ByteArray>()
		val header = ByteArray(BLOCK)
		while (readFully(input, header) == BLOCK) {
			if (header.all { it == 0.toByte() }) break
			val name = String(header, 0, 100, Charsets.UTF_8).trimEnd('\u0000')
			val prefix = String(header, 345, 155, Charsets.UTF_8).trimEnd('\u0000')
			val full = if (prefix.isEmpty()) name else "$prefix/$name"
			val size = String(header, 124, 11, Charsets.US_ASCII).trim().trim('\u0000').toLong(8)
			val type = header[156].toInt().toChar()
			val padded = (size + BLOCK - 1) / BLOCK * BLOCK
			if ((type == '0' || type == '\u0000') && wanted(full)) {
				val data = ByteArray(size.toInt())
				check(readFully(input, data) == data.size) { "truncated tar" }
				found[full] = data
				skip(input, padded - size)
			} else {
				skip(input, padded)
			}
		}
		return found
	}

	private fun put(target: ByteArray, at: Int, text: String) = text.toByteArray(Charsets.US_ASCII).copyInto(target, at)

	private fun readFully(input: InputStream, buffer: ByteArray): Int {
		var n = 0
		while (n < buffer.size) {
			val r = input.read(buffer, n, buffer.size - n)
			if (r < 0) break
			n += r
		}
		return n
	}

	private fun skip(input: InputStream, count: Long) {
		var left = count
		val scratch = ByteArray(8192)
		while (left > 0) {
			val r = input.read(scratch, 0, minOf(left, scratch.size.toLong()).toInt())
			if (r < 0) break
			left -= r
		}
	}
}
