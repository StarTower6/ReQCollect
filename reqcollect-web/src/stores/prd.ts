import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PrdRecord } from '@/types'
import { fetchPrd } from '@/api/prd'

export const usePrdStore = defineStore('prd', () => {
  const prd = ref<PrdRecord | null>(null)

  async function load(sessionId: string) {
    prd.value = await fetchPrd(sessionId)
  }

  function clear() {
    prd.value = null
  }

  return { prd, load, clear }
})
