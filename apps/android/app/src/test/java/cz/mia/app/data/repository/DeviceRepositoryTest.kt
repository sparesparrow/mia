package cz.mia.app.data.repository

import cz.mia.app.data.remote.api.DeviceApi
import cz.mia.app.data.remote.dto.CommandResponse
import cz.mia.app.data.remote.dto.DeviceDto
import cz.mia.app.data.remote.dto.DeviceListResponse
import cz.mia.app.data.remote.dto.DeviceStatus
import cz.mia.app.data.remote.dto.SingleDeviceResponse
import cz.mia.app.data.remote.dto.SystemStatus
import cz.mia.app.data.remote.dto.MemoryInfo
import cz.mia.app.data.remote.dto.CpuInfo
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import org.mockito.kotlin.any
import org.mockito.kotlin.anyOrNull
import org.mockito.kotlin.mock
import org.mockito.kotlin.whenever
import retrofit2.Response
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class DeviceRepositoryTest {

    private lateinit var deviceApi: DeviceApi
    private lateinit var repository: DeviceRepository

    @Before
    fun setup() {
        deviceApi = mock()
        repository = DeviceRepository(deviceApi)
    }

    @Test
    fun `getDevices unwraps DeviceListResponse envelope`() = runTest {
        val devices = listOf(
            DeviceDto(
                deviceId = "esp32-obd-001",
                name = "OBD Bridge",
                deviceType = "obd",
                status = DeviceStatus.ONLINE,
                capabilities = listOf("read_pids", "dtc_clear")
            )
        )
        whenever(deviceApi.getDevices(anyOrNull(), anyOrNull())).thenReturn(
            Response.success(DeviceListResponse(devices = devices, count = 1, timestamp = "2026-03-12T10:00:00"))
        )

        val result = repository.getDevices()
        assertTrue(result.isSuccess)
        assertEquals(1, result.getOrThrow().size)
        assertEquals("esp32-obd-001", result.getOrThrow()[0].deviceId)
        assertEquals("obd", result.getOrThrow()[0].deviceType)
    }

    @Test
    fun `getDevice unwraps SingleDeviceResponse envelope`() = runTest {
        val device = DeviceDto(
            deviceId = "pi-gateway-001",
            name = "Pi Gateway",
            deviceType = "gpio",
            status = DeviceStatus.ONLINE
        )
        whenever(deviceApi.getDevice(any())).thenReturn(
            Response.success(SingleDeviceResponse(device = device, timestamp = "2026-03-12T10:00:00"))
        )

        val result = repository.getDevice("pi-gateway-001")
        assertTrue(result.isSuccess)
        assertEquals("pi-gateway-001", result.getOrThrow().deviceId)
    }

    @Test
    fun `getSystemStatus parses nested memory and cpu`() = runTest {
        val status = SystemStatus(
            status = "healthy",
            uptimeSeconds = 86400,
            memory = MemoryInfo(total = 4_000_000_000, available = 2_000_000_000, percent = 50.0, used = 2_000_000_000),
            cpu = CpuInfo(percent = 15.5, count = 4),
            devicesConnected = 3,
            timestamp = "2026-03-12T10:00:00"
        )
        whenever(deviceApi.getSystemStatus()).thenReturn(Response.success(status))

        val result = repository.getSystemStatus()
        assertTrue(result.isSuccess)
        assertEquals("healthy", result.getOrThrow().status)
        assertEquals(50.0, result.getOrThrow().memory?.percent)
        assertEquals(4, result.getOrThrow().cpu?.count)
    }

    @Test
    fun `sendCommand uses device_id field`() = runTest {
        whenever(deviceApi.sendCommand(any())).thenReturn(
            Response.success(CommandResponse(success = true, timestamp = "2026-03-12T10:00:00"))
        )

        val result = repository.sendCommand("esp32-obd-001", "read_dtc")
        assertTrue(result.isSuccess)
        assertTrue(result.getOrThrow().success)
    }

    @Test
    fun `getDevices returns error on network failure`() = runTest {
        whenever(deviceApi.getDevices(anyOrNull(), anyOrNull())).thenThrow(RuntimeException("Connection refused"))

        val result = repository.getDevices()
        assertTrue(result.isError)
    }
}
