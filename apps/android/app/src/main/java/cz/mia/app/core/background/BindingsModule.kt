package cz.mia.app.core.background

import cz.mia.app.core.rules.RulesEngine
import cz.mia.app.core.rules.RulesEngineImpl
import cz.mia.app.core.voice.VoiceManager
import cz.mia.app.core.voice.VoiceManagerImpl
import cz.mia.app.data.repositories.EventRepository
import cz.mia.app.data.repositories.EventRepositoryImpl
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class BindingsModule {
	@Binds
	@Singleton
	abstract fun bindBleManager(impl: BLEManagerImpl): BLEManager

	@Binds
	@Singleton
	abstract fun bindMqttManager(impl: MQTTManagerImpl): MQTTManager

	@Binds
	@Singleton
	abstract fun bindObdManager(impl: OBDManagerImpl): OBDManager

	@Binds
	@Singleton
	abstract fun bindAnprManager(impl: ANPRManagerImpl): ANPRManager

	@Binds
	@Singleton
	abstract fun bindVoiceManager(impl: VoiceManagerImpl): VoiceManager

	@Binds
	@Singleton
	abstract fun bindRulesEngine(impl: RulesEngineImpl): RulesEngine

	@Binds
	@Singleton
	abstract fun bindEventRepository(impl: EventRepositoryImpl): EventRepository

	@Binds
	@Singleton
	abstract fun bindDVRManager(impl: DVRManagerImpl): DVRManager

	@Binds
	@Singleton
	abstract fun bindSystemPolicyManager(impl: SystemPolicyManagerImpl): SystemPolicyManager
}
