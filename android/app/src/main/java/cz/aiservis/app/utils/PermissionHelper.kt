package cz.aiservis.app.utils

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.content.ContextCompat

/**
 * Helper object for managing runtime permissions, particularly for Bluetooth.
 * Handles the different permission requirements for Android versions.
 */
object PermissionHelper {

    private const val TAG = "PermissionHelper"
    /**
     * Get the required Bluetooth permissions based on Android version.
     * - Android 12+ (API 31+): BLUETOOTH_SCAN, BLUETOOTH_CONNECT
     * - Android 10-11 (API 29-30): ACCESS_FINE_LOCATION
     * - Android 6-9 (API 23-28): ACCESS_COARSE_LOCATION
     */
    fun getRequiredBluetoothPermissions(): Array<String> {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                // Android 12+ requires new Bluetooth permissions
                arrayOf(
                    Manifest.permission.BLUETOOTH_SCAN,
                    Manifest.permission.BLUETOOTH_CONNECT
                )
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                // Android 10-11 requires fine location for BLE scanning
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
            } else {
                // Android 6-9 can use coarse location
                arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting permissions", e)
            emptyArray()
        }
    }

    /**
     * Get all Bluetooth-related permissions that may be needed.
     * This returns a comprehensive list for permission requests.
     */
    fun getAllBluetoothPermissions(): Array<String> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        } else {
            arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
        }
    }

    /**
     * Check if all required Bluetooth permissions are granted.
     */
    fun hasBluetoothPermissions(context: Context): Boolean {
        return try {
            val permissions = getRequiredBluetoothPermissions()
            if (permissions.isEmpty()) return true
            permissions.all { permission ->
                ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error checking permissions", e)
            true // Return true to allow initialization to proceed
        }
    }

    /**
     * Get list of missing Bluetooth permissions.
     */
    fun getMissingBluetoothPermissions(context: Context): List<String> {
        return try {
            getRequiredBluetoothPermissions().filter { permission ->
                ContextCompat.checkSelfPermission(context, permission) != PackageManager.PERMISSION_GRANTED
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting missing permissions", e)
            emptyList()
        }
    }

    /**
     * Check if a specific permission is granted.
     */
    fun hasPermission(context: Context, permission: String): Boolean {
        return ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Check if camera permission is granted.
     */
    fun hasCameraPermission(context: Context): Boolean {
        return hasPermission(context, Manifest.permission.CAMERA)
    }

    /**
     * Check if notification permission is granted (Android 13+).
     */
    fun hasNotificationPermission(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            hasPermission(context, Manifest.permission.POST_NOTIFICATIONS)
        } else {
            true // Not required before Android 13
        }
    }

    /**
     * Get notification permission if needed (Android 13+).
     */
    fun getNotificationPermission(): String? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            Manifest.permission.POST_NOTIFICATIONS
        } else {
            null
        }
    }

    /**
     * Check if location permission is granted.
     */
    fun hasLocationPermission(context: Context): Boolean {
        return hasPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ||
                hasPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
    }

    /**
     * Get all permissions needed for the app's full functionality.
     */
    fun getAllRequiredPermissions(): Array<String> {
        val permissions = mutableListOf<String>()
        
        // Bluetooth permissions
        permissions.addAll(getAllBluetoothPermissions())
        
        // Camera permission
        permissions.add(Manifest.permission.CAMERA)
        
        // Notification permission (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        
        return permissions.toTypedArray()
    }

    /**
     * Get all missing permissions from the required set.
     */
    fun getAllMissingPermissions(context: Context): List<String> {
        return getAllRequiredPermissions().filter { permission ->
            ContextCompat.checkSelfPermission(context, permission) != PackageManager.PERMISSION_GRANTED
        }
    }
}
