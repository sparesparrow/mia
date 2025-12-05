package cz.mia.app.features.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cz.mia.app.core.background.SystemPolicyManager
import cz.mia.app.core.background.SystemPolicyState
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class PolicyViewModel @Inject constructor(
	policy: SystemPolicyManager
) : ViewModel() {
	val state = policy.state.stateIn(
		viewModelScope,
		SharingStarted.Eagerly,
		SystemPolicyState(
			samplingMode = cz.mia.app.core.background.SamplingMode.NORMAL,
			thermalSeverity = cz.mia.app.core.background.ThermalSeverity.NONE,
			isPowerSaveMode = false,
			batteryPercent = 100,
			advisoryMessage = null
		)
	)
}


