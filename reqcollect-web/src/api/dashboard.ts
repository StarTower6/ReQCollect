import { apiGet } from './client'
import type { DashboardOverview, TrendPoint } from '@/types'

export async function fetchOverview(): Promise<DashboardOverview> {
  const data = await apiGet<{ success: boolean; data: DashboardOverview }>('/pm/dashboard/overview')
  return data.data
}

export async function fetchTrend(granularity = 'day', days = 30): Promise<TrendPoint[]> {
  const data = await apiGet<{ success: boolean; data: TrendPoint[] }>(
    `/pm/dashboard/trend?granularity=${granularity}&days=${days}`
  )
  return data.data
}
