package cz.mia.app.data.repositories

import cz.mia.app.data.db.AuditDao
import cz.mia.app.data.db.AuditEventEntity
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow

@Singleton
class AuditRepository @Inject constructor(
	private val dao: AuditDao
) {
	suspend fun record(category: String, action: String, details: String? = null) {
		dao.insert(
			AuditEventEntity(
				ts = System.currentTimeMillis(),
				category = category,
				action = action,
				details = details
			)
		)
	}

	fun recent(limit: Int = 100): Flow<List<AuditEventEntity>> = dao.recent(limit)
}
