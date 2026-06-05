import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RequirementProfile } from '@/types'
import { fetchProfile } from '@/api/profile'

const PROFILE_DEFAULTS: RequirementProfile = {
  project_name: '',
  business_background: '',
  current_process: '',
  user_roles: [],
  business_flow: '',
  functional_requirements: [],
  existing_systems: [],
  non_functional: {},
  data_scale: '',
  constraints: [],
  success_criteria: [],
  covered_topics: [],
  pending_questions: [],
  sufficiency_score: 0,
}

export const useProfileStore = defineStore('profile', () => {
  const profile = ref<RequirementProfile>({ ...PROFILE_DEFAULTS })

  async function load(sessionId: string) {
    try {
      profile.value = await fetchProfile(sessionId)
    } catch {
      profile.value = { ...PROFILE_DEFAULTS }
    }
  }

  function updateSufficiency(score: number) {
    profile.value.sufficiency_score = score
  }

  function clear() {
    profile.value = { ...PROFILE_DEFAULTS }
  }

  return { profile, load, updateSufficiency, clear }
})
