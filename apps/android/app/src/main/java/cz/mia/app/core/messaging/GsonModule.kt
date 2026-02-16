package cz.mia.app.core.messaging

import com.google.gson.Gson
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object GsonModule {
	@Provides
	@Singleton
	fun provideGson(): Gson = Gson()
}
