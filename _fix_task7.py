import pathlib

# ── Fix proposal.ts signature ──
pts = pathlib.Path("reqcollect-web/src/api/proposal.ts")
pts_content = pts.read_text(encoding="utf-8")

old_sig = """  onDone: (data: any) => void,
  onError: (err: string) => void,
): Promise<void> {"""

new_sig = """  onDone: (data: any) => void,
  onError: (err: string) => void,
  onThought?: (text: string) => void,
  onSectionContent?: (chunk: string) => void,
): Promise<void> {"""

pts_content = pts_content.replace(old_sig, new_sig, 1)
pts.write_text(pts_content, encoding="utf-8")
print("proposal.ts: signature fixed with onThought + onSectionContent")

# ── Fix ProposalListView.vue ──
plv_path = pathlib.Path("reqcollect-web/src/views/proposal/ProposalListView.vue")
plv = plv_path.read_text(encoding="utf-8")

# 1. Replace dialog template
old_dialog = """    <!-- PRD 生成进度对话框 -->
    <el-dialog v-model="showPrdDialog" title="生成 PRD" width="480px" :close-on-click-modal="false" :close-on-press-escape="false">
      <div class="prd-gen-content">
        <div v-if="prdGenerating" class="prd-gen-progress">
          <el-progress :percentage="prdSectionTotal > 0 ? Math.round(prdSectionIndex / prdSectionTotal * 100) : 0" :stroke-width="8" />
          <p class="prd-gen-status">{{ prdProgress }}</p>
          <div v-if="prdSection" class="prd-gen-section">
            <span class="prd-gen-section-label">当前章节:</span>
            <span class="prd-gen-section-title">{{ prdSection }}</span>
          </div>
        </div>
        <div v-else-if="prdProgress.includes('完成')" class="prd-gen-done">
          <el-result icon="success" title="PRD 生成完成" sub-title="点击下方按钮查看生成的 PRD 文档" />
        </div>
        <div v-else class="prd-gen-error">
          <el-result icon="error" title="生成失败" :sub-title="prdProgress || '请重试'" />
        </div>
      </div>
      <template #footer>
        <el-button v-if="!prdGenerating" @click="showPrdDialog = false">关闭</el-button>
        <el-button v-if="createdPrdId" type="primary" @click="goToPrd">查看 PRD</el-button>
      </template>
    </el-dialog>"""

new_dialog = """    <!-- PRD 生成进度对话框 -->
    <el-dialog v-model="showPrdDialog" title="\u751f\u6210 PRD" width="900px" :close-on-click-modal="false">
      <div class="prd-gen-dialog">
        <div class="prd-gen-left">
          <div v-if="prdGenerating" class="prd-gen-progress-small">
            <el-progress :percentage="prdSectionTotal > 0 ? Math.round(prdSectionIndex / prdSectionTotal * 100) : 0" :stroke-width="8" />
            <p class="prd-gen-status">{{ prdProgress }}</p>
          </div>
          <div v-else-if="prdProgress.includes('\u5b8c\u6210')" class="prd-gen-done">
            <el-result icon="success" title="PRD \u751f\u6210\u5b8c\u6210" sub-title="\u70b9\u51fb\u4e0b\u65b9\u6309\u94ae\u67e5\u770b PRD" />
          </div>
          <div class="prd-gen-thoughts" v-if="thoughts.length > 0">
            <div class="prd-gen-thoughts-title">\ud83d\udcad \u601d\u8003\u8fc7\u7a0b</div>
            <div v-for="(t, i) in thoughts" :key="i" class="thought-item">{{ t }}</div>
          </div>
        </div>
        <div class="prd-gen-right">
          <div class="prd-gen-preview-title">\ud83d\udcc4 \u5b9e\u65f6\u9884\u89c8</div>
          <div class="prd-gen-preview" v-html="renderedPreview" v-if="renderedPreview"></div>
          <div v-else class="prd-gen-preview-empty">\u5f85\u751f\u6210\u5f00\u59cb\u540e\uff0c\u9884\u89c8\u5c06\u5728\u6b64\u5904\u663e\u793a</div>
        </div>
      </div>
      <template #footer>
        <el-button v-if="!prdGenerating" @click="showPrdDialog = false">\u5173\u95ed</el-button>
        <el-button v-if="createdPrdId" type="primary" @click="goToPrd">\u67e5\u770b PRD</el-button>
      </template>
    </el-dialog>"""

plv = plv.replace(old_dialog, new_dialog, 1)

# 2. Add marked import + new state vars
old_import = "import { useAuthStore } from '@/stores/auth'"
new_import = "import { useAuthStore } from '@/stores/auth'\nimport { marked } from 'marked'"
plv = plv.replace(old_import, new_import, 1)

old_state = """const showPrdDialog = ref(false)
const prdGenerating = ref(false)
const prdProgress = ref('')
const prdSection = ref('')
const prdSectionTotal = ref(0)
const prdSectionIndex = ref(0)
let createdPrdId = ''"""

new_state = """const showPrdDialog = ref(false)
const prdGenerating = ref(false)
const prdProgress = ref('')
const prdSection = ref('')
const prdSectionTotal = ref(0)
const prdSectionIndex = ref(0)
let createdPrdId = ''
const thoughts = ref<string[]>([])
const previewMarkdown = ref('')
const renderedPreview = ref('')"""

plv = plv.replace(old_state, new_state, 1)

# 3. Update generatePrd function
old_gen = """  await generatePrdFromProposalsSSE(
    wid,
    selectedIds.value,
    (msg) => { prdProgress.value = msg },
    (title, index, total) => {
      prdSection.value = title
      prdSectionIndex.value = index
      prdSectionTotal.value = total
      prdProgress.value = `正在撰写第 ${index}/${total} 章: ${title}`
    },
    (data) => {
      createdPrdId = data?.prd_id || ''
      prdGenerating.value = false
      prdProgress.value = '\u2705 PRD 生成完成！'
      ElMessage.success('PRD 生成完成')
    },
    (err) => {
      prdGenerating.value = false
      prdProgress.value = ''
      ElMessage.error(err || 'PRD 生成失败')
    },
  )"""

new_gen = """  await generatePrdFromProposalsSSE(
    wid,
    selectedIds.value,
    (msg) => { prdProgress.value = msg },
    (title, index, total) => {
      prdSection.value = title
      prdSectionIndex.value = index
      prdSectionTotal.value = total
      prdProgress.value = `正在撰写第 ${index}/${total} 章: ${title}`
    },
    (data) => {
      createdPrdId = data?.prd_id || data?.id || ''
      prdGenerating.value = false
      prdProgress.value = '\u2705 PRD 生成完成！'
      ElMessage.success('PRD 生成完成')
    },
    (err) => {
      prdGenerating.value = false
      prdProgress.value = ''
      ElMessage.error(err || 'PRD 生成失败')
    },
    (thoughtText) => {
      thoughts.value.push(thoughtText)
    },
    (chunk: string) => {
      previewMarkdown.value += chunk
      renderedPreview.value = marked.parse(previewMarkdown.value, { async: false }) as string
    },
  )"""

plv = plv.replace(old_gen, new_gen, 1)

# 4. Clear thoughts/preview in generatePrd
old_clear = "  createdPrdId = ''"
new_clear = "  createdPrdId = ''\n  thoughts.value = []\n  previewMarkdown.value = ''\n  renderedPreview.value = ''"
plv = plv.replace(old_clear, new_clear, 1)

# 5. Update goToPrd (already correct, just ensure prd_id fallback)
# Already: `if (createdPrdId) { router.push(`/prd/${createdPrdId}`) }` — ok

# 6. Fix CSS
old_css = """/* ── PRD 生成对话框 ── */
.prd-gen-content { min-height: 120px; display: flex; align-items: center; justify-content: center; }
.prd-gen-progress { width: 100%; padding: 16px 0; }
.prd-gen-status { text-align: center; font-size: 14px; color: var(--text); margin: 16px 0 8px; }
.prd-gen-section { text-align: center; font-size: 13px; color: var(--muted); }
.prd-gen-section-label { margin-right: 4px; }
.prd-gen-section-title { font-weight: 500; color: var(--brand); }
.prd-gen-done, .prd-gen-error { width: 100%; }

.prd-gen-dialog { display: flex; gap: 16px; min-height: 400px; }
.prd-gen-left { flex: 0 0 280px; display: flex; flex-direction: column; gap: 12px; }
.prd-gen-right { flex: 1; border: 1px solid var(--line); border-radius: 8px; padding: 16px; overflow-y: auto; max-height: 60vh; background: var(--bg); }
.prd-gen-thoughts { max-height: 200px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.thought-item { font-size: 13px; color: var(--brand); padding: 4px 8px; background: color-mix(in srgb, var(--brand) 8%, transparent); border-radius: 6px; }
.prd-gen-status { font-size: 14px; color: var(--text); margin: 0; }
.prd-gen-empty { text-align: center; color: var(--muted); padding-top: 40px; }"""

new_css = """/* ── PRD 生成对话框 ── */
.prd-gen-dialog { display: flex; gap: 16px; min-height: 400px; }
.prd-gen-left { flex: 0 0 280px; display: flex; flex-direction: column; gap: 12px; }
.prd-gen-right { flex: 1; border: 1px solid var(--line); border-radius: 8px; padding: 20px; overflow-y: auto; max-height: 60vh; background: var(--bg); }
.prd-gen-progress-small { width: 100%; }
.prd-gen-status { font-size: 13px; color: var(--text); margin: 8px 0; text-align: center; }
.prd-gen-done { width: 100%; }
.prd-gen-thoughts { max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.prd-gen-thoughts-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.thought-item { font-size: 12px; color: var(--brand); padding: 6px 10px; background: color-mix(in srgb, var(--brand) 10%, transparent); border-radius: 6px; line-height: 1.5; }
.prd-gen-preview-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 12px; }
.prd-gen-preview { font-size: 13px; line-height: 1.7; color: var(--text); }
.prd-gen-preview-empty { text-align: center; color: var(--muted); padding-top: 60px; font-size: 14px; }"""

plv = plv.replace(old_css, new_css, 1)
plv_path.write_text(plv, encoding="utf-8")
print("ProposalListView.vue: dialog refactored to dual-panel")
print("Done!")
