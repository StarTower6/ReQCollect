<template>
  <div class="dashboard" style="height:100vh">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <router-link to="/chat" class="sidebar-link" style="text-decoration:none">← 返回对话</router-link>
      <div style="font-size:20px;font-weight:760">数据看板</div>
    </div>

    <div class="dashboard-grid" v-if="overview">
      <div class="stat-card">
        <div class="stat-value">{{ overview.total_sessions }}</div>
        <div class="stat-label">总会话数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ overview.total_prds }}</div>
        <div class="stat-label">PRD 生成数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ overview.total_messages }}</div>
        <div class="stat-label">消息总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ (overview.avg_sufficiency * 100).toFixed(0) }}%</div>
        <div class="stat-label">平均完整度</div>
      </div>
    </div>

    <div class="chart-card">
      <div ref="trendChartRef" style="width:100%;height:320px"></div>
    </div>

    <div class="chart-card" v-if="overview">
      <div ref="statusChartRef" style="width:100%;height:240px"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { fetchOverview, fetchTrend } from '@/api/dashboard'
import type { DashboardOverview, TrendPoint } from '@/types'

const overview = ref<DashboardOverview | null>(null)
const trendChartRef = ref<HTMLElement | null>(null)
const statusChartRef = ref<HTMLElement | null>(null)

function renderTrendChart(data: TrendPoint[]) {
  if (!trendChartRef.value) return
  nextTick(() => {
    const chart = echarts.init(trendChartRef.value!)
    chart.setOption({
      title: { text: '会话与 PRD 趋势', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, data: ['会话数', 'PRD 数'] },
      xAxis: { type: 'category', data: data.map(d => d.date) },
      yAxis: { type: 'value', minInterval: 1 },
      grid: { left: 50, right: 20, top: 40, bottom: 40 },
      series: [
        { name: '会话数', type: 'bar', data: data.map(d => d.sessions), itemStyle: { color: '#3f7df6' } },
        { name: 'PRD 数', type: 'line', data: data.map(d => d.prds), smooth: true, itemStyle: { color: '#36b37e' } },
      ],
    })
  })
}

function renderStatusChart(ov: DashboardOverview) {
  if (!statusChartRef.value) return
  nextTick(() => {
    const chart = echarts.init(statusChartRef.value!)
    const statusMap: Record<string, string> = { mining: '采集中', generating: '生成中', complete: '已完成' }
    const data = Object.entries(ov.by_status).map(([k, v]) => ({ name: statusMap[k] || k, value: v }))
    chart.setOption({
      title: { text: '会话状态分布', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item', formatter: '{b}: {c}' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '55%'],
        data,
        label: { show: true, formatter: '{b}: {c}' },
      }],
    })
  })
}

onMounted(async () => {
  overview.value = await fetchOverview()
  const trend = await fetchTrend('day', 30)
  renderTrendChart(trend)
  if (overview.value) renderStatusChart(overview.value)
})
</script>
