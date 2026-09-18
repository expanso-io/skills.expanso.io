# Server Room Cooling Runbook (synthetic)

The server room uses hot-aisle containment with four computer room air handlers. Blanking panels must fill every empty rack unit, because gaps let exhaust air recirculate into the cold aisle.

Cold-aisle inlet temperature is monitored at the top of every third rack. A warning is raised at 25 degrees Celsius and a critical cooling alarm fires at 27 degrees Celsius sustained for five minutes.

When the critical alarm fires, the on-call engineer confirms which air handler has failed, opens the standby unit, and throttles batch workloads on the affected row. Doors to the hot aisle stay closed during the response.

Air handler filters are replaced every 90 days and after any construction work in the building, whichever comes first.
