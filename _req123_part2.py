"""
Requirements 2 & 3:
  2. ProposalListView — three-phase dialog
  3. PrdView — Markdown edit mode
"""
import pathlib

ROOT = pathlib.Path(r"G:\claude-code-workspace\ReqCollect")
LOG = []

def log(msg):
    LOG.append(msg)
    print(msg)

# ════════════════════════════════════════════════════════════════
# REQUIREMENT 2: ProposalListView three-phase dialog
# ════════════════════════════════════════════════════════════════
prop_path = ROOT / "reqcollect-web" / "src" / "views" / "proposal" / "ProposalListView.vue"
prop = prop_path.read_text("utf-8")

# ---- 2a. Replace the dialog template ----
old_dialog_start = '''  <!-- PRD 生成对话框 — 双栏: 思考过程 + 实时预览 -->
  <el-dialog v-model="showPrdDialog" title="生成 PRD" width="900px" :close-on-click-modal="false" :close-on-press-escape="false">
    <div class="prd-gen-body" v-if="showPrdDialog">
      <div class="prd-gen-status-bar">
        <el-progress :percentage="prdSectionTotal > 0 ? Math.round(prdSectionIndex / prdSectionTotal * 100) : 0" :stroke-width="8" />
        <p class="prd-gen-status">{{ prdProgress }}</p>
        <div v-if="prdSection" class="prd-gen-section">
          <span class="prd-gen-section-label">当前章节:</span>
          <span class="prd-gen-section-title">{{ prdSection }}</span>
        </div>
      </div>
      <div class="prd-gen-dual">
        <div class="prd-gen-left">
          <div class="prd-gen-side-title">💭 思考过程</div>
          <div class="prd-gen-thoughts" ref="thoughtsBox">
            <div v-for="(t, i) in thoughts" :key="i" class="thought-item">{{ t }}</div>
          </div>
        </div>
        <div class="prd-gen-right">
          <div class="prd-gen-side-title">📄 实时预览</div>
          <div class="prd-gen-preview" ref="previewBox" v-html="renderedPreview"></div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="showPrdDialog = false" :disabled="prdGenerating">关闭</el-button>
    </template>
  </el-dialog>'''

new_dialog = '''  <!-- PRD 生成对话框 — 三阶段: 生成中 / 完成 / 失败 -->
  <el-dialog v-model="showPrdDialog" title="生成 PRD" width="900px" :close-on-click-modal="false" :close-on-press-escape="false">
    <!-- 阶段1: 生成中 -->
    <div v-if="prdGenerating" class="prd-gen-loading">
      <div class="prd-gen-status-bar">
        <el-progress :percentage="prdSectionTotal > 0 ? Math.round(prdSectionIndex / prdSectionTotal * 100) : 0" :stroke-width="8" />
        <p class="prd-gen-status">{{ prdProgress }}</p>
        <div v-if="prdSection" class="prd-gen-section">
          <span class="prd-gen-section-label">当前章节:</span>
          <span class="prd-gen-section-title">{{ prdSection }}</span>
        </div>
      </div>
      <div class="prd-gen-dual">
        <div class="prd-gen-left">
          <div class="prd-gen-side-title">💭 思考过程</div>
          <div class="prd-gen-thoughts" ref="thoughtsBox">
            <div v-for="(t, i) in thoughts" :key="i" class="thought-item">{{ t }}</div>
          </div>
        </div>
        <div class="prd-gen-right">
          <div class="prd-gen-side-title">📄 实时预览</div>
          <div class="prd-gen-preview" ref="previewBox" v-html="renderedPreview"></div>
        </div>
      </div>
    </div>

    <!-- 阶段2: 完成 -->
    <div v-else-if="prdGenStatus === 'done'" class="prd-gen-done">
      <el-result icon="success" title="PRD 生成完成" sub-title="点击下方按钮查看生成的 PRD 文档" />
    </div>

    <!-- 阶段3: 失败 -->
    <div v-else-if="prdGenStatus === 'error'" class="prd-gen-error">
      <el-result icon="error" title="生成失败" :sub-title="prdProgress || '请重试'" />
    </div>

    <template #footer>
      <el-button v-if="!prdGenerating" @click="showPrdDialog = false">关闭</el-button>
      <el-button v-if="prdGenStatus === 'done' && createdPrdId" type="primary" @click="goToPrd">查看 PRD &rarr;</el-button>
      <el-button v-if="prdGenStatus === 'error'" type="primary" @click="generatePrd">重试</el-button>
    </template>
  </el-dialog>'''

if old_dialog_start in prop:
    prop = prop.replace(old_dialog_start, new_dialog)
    log("OK ProposalListView: replaced dialog template with 3-phase")
else:
    log("WARN ProposalListView: old dialog not found — trying partial match")
    # Try to find by key markers
    if 'prd-gen-body' in prop:
        log("  Found prd-gen-body in template — needs manual update")
    else:
        log("  prd-gen-body not found either")

# ---- 2b. Add prdGenStatus and createdPrdId state ----
# Insert after thoughts refs
old_state = '''const previewMarkdown = ref<string[]>([])
const renderedPreview = ref('')'''

new_state = '''const previewMarkdown = ref<string[]>([])
const renderedPreview = ref('')
const prdGenStatus = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
const createdPrdId = ref('')'''

if old_state in prop:
    prop = prop.replace(old_state, new_state)
    log("OK ProposalListView: added prdGenStatus + createdPrdId state")
else:
    log("WARN ProposalListView: state anchor not found")

# ---- 2c. Add watch imports and auto-scroll ----
# Insert after the marked import
old_marked_import = "import { marked } from 'marked'"
new_marked_import = '''import { marked } from 'marked'
import { watch, nextTick } from 'vue''

if old_marked_import in prop and "import { watch, nextTick }" not in prop:
    prop = prop.replace(
        old_marked_import,
        new_marked_import,
    )
    log("OK ProposalListView: added watch/nextTick import")
else:
    log("SKIP ProposalListView: watch/nextTick already imported")

# ---- 2d. Add auto-scroll watchers ----
# Insert after the generatePrd function
old_generate_end = """      prdGenerating.value = false
    }
  })"""

new_generate_end = """      prdGenerating.value = false
      prdGenStatus.value = 'done'
    }
  })
}

// Auto-scroll watchers
const thoughtsBox = ref<HTMLElement | null>(null)
const previewBox = ref<HTMLElement | null>(null)

watch(thoughts, async () => {
  await nextTick()
  if (thoughtsBox.value) thoughtsBox.value.scrollTop = thoughtsBox.value.scrollHeight
}, { deep: true })

watch(renderedPreview, async () => {
  await nextTick()
  if (previewBox.value) previewBox.value.scrollTop = previewBox.value.scrollHeight
})"""

if old_generate_end in prop:
    prop = prop.replace(old_generate_end, new_generate_end)
    log("OK ProposalListView: added auto-scroll watchers")
else:
    log("WARN ProposalListView: generateEnd anchor not found")

# ---- 2e. Fix generatePrd start to set prdGenStatus ----
old_gen_start = """  prdGenerating.value = true
  prdProgress.value = '正在启动 PRD 生成...'
  prdSection.value = ''
  prdSectionIndex.value = 0
  prdSectionTotal.value = 0
  thoughts.value = []
  previewMarkdown.value = []
  renderedPreview.value = ''"""

new_gen_start = """  prdGenerating.value = true
  prdGenStatus.value = 'loading'
  createdPrdId.value = ''
  prdProgress.value = '正在启动 PRD 生成...'
  prdSection.value = ''
  prdSectionIndex.value = 0
  prdSectionTotal.value = 0
  thoughts.value = []
  previewMarkdown.value = []
  renderedPreview.value = ''"""

if old_gen_start in prop:
    prop = prop.replace(old_gen_start, new_gen_start)
    log("OK ProposalListView: set prdGenStatus=loading on start")
else:
    log("WARN ProposalListView: gen_start anchor not found")

# ---- 2f. Fix onError to set prdGenStatus ----
old_on_error = """    onError: (msg) => {
      prdProgress.value = msg
      prdGenerating.value = false
    }"""

new_on_error = """    onError: (msg) => {
      prdProgress.value = msg
      prdGenerating.value = false
      prdGenStatus.value = 'error'
    }"""

if old_on_error in prop:
    prop = prop.replace(old_on_error, new_on_error)
    log("OK ProposalListView: set prdGenStatus=error on error")
else:
    log("WARN ProposalListView: onError anchor not found")

# ---- 2g. Fix onDone to set prdGenStatus and createdPrdId ----
old_on_done = '''    onDone: () => {
      prdGenerating.value = false
    }'''

new_on_done = '''    onDone: () => {
      prdGenerating.value = false
      prdGenStatus.value = 'done'
    }'''

if old_on_done in prop:
    prop = prop.replace(old_on_done, new_on_done)
    log("OK ProposalListView: set prdGenStatus=done on done")
else:
    log("WARN ProposalListView: onDone anchor not found")

# ---- 2h. Add goToPrd function ----
old_close_gen = "const closeGen = () => {"

new_close_gen = """const goToPrd = () => {
  showPrdDialog.value = false
  if (createdPrdId.value) {
    router.push(`/prd/${createdPrdId.value}`)
  }
}

const closeGen = () => {"""

if old_close_gen in prop and "const goToPrd" not in prop:
    prop = prop.replace(old_close_gen, new_close_gen)
    log("OK ProposalListView: added goToPrd function")
else:
    log("SKIP ProposalListView: goToPrd already exists or anchor not found")

prop_path.write_text(prop, "utf-8")
log("\n=== Requirement 2 done ===")

# ════════════════════════════════════════════════════════════════
# REQUIREMENT 3: PrdView Markdown edit mode
# ════════════════════════════════════════════════════════════════
prdview_path = ROOT / "reqcollect-web" / "src" / "views" / "PrdView.vue"
prdview = prdview_path.read_text("utf-8")

# ---- 3a. Add edit mode section in template ----
# Replace the PRD content section to include edit mode
old_content_section = '''    <div v-else class="prd-content" ref="prdContentRef" v-html="renderedMarkdown"></div>'''

new_content_section = '''    <!-- 查看模式 -->
    <div v-else-if="!editing" class="prd-content" ref="prdContentRef" v-html="renderedMarkdown"></div>
    
    <!-- 编辑模式: 左编辑器 + 右预览 -->
    <div v-else class="prd-edit-dual">
      <div class="prd-edit-left">
        <textarea v-model="editMarkdown" class="prd-edit-textarea" placeholder="输入 Markdown..."></textarea>
      </div>
      <div class="prd-edit-right">
        <div class="prd-content" v-html="editRenderedPreview"></div>
      </div>
    </div>'''

if old_content_section in prdview:
    prdview = prdview.replace(old_content_section, new_content_section)
    log("OK PrdView: added edit mode template")
else:
    log("WARN PrdView: content section anchor not found")

# ---- 3b. Replace action buttons ----
old_actions = '''      <div class="prd-actions">
        <el-button size="small" :loading="wikiLoading" @click="showWikiDialog = true">📄 加入 Wiki</el-button>
      </div>'''

new_actions = '''      <div class="prd-actions">
        <el-button v-if="!editing" size="small" @click="startEdit">✏️ 编辑</el-button>
        <template v-else>
          <el-button size="small" @click="cancelEdit">取消</el-button>
          <el-button size="small" type="primary" :loading="saving" @click="saveEdit">保存</el-button>
        </template>
        <el-button v-if="!editing" size="small" :loading="wikiLoading" @click="showWikiDialog = true">📄 加入 Wiki</el-button>
      </div>'''

if old_actions in prdview:
    prdview = prdview.replace(old_actions, new_actions)
    log("OK PrdView: replaced action buttons with edit controls")
else:
    log("WARN PrdView: actions anchor not found")

# ---- 3c. Add PrdToc conditional ----
old_toc = '''    <div class="prd-main">
      <PrdToc v-if="prdStore.prd && prdStore.prd.sections" :sections="prdStore.prd.sections" />'''

new_toc = '''    <div class="prd-main">
      <PrdToc v-if="prdStore.prd && prdStore.prd.sections && !editing" :sections="prdStore.prd.sections" />'''

if old_toc in prdview:
    prdview = prdview.replace(old_toc, new_toc)
    log("OK PrdView: hide PrdToc in edit mode")
else:
    log("WARN PrdView: PrdToc anchor not found")

# ---- 3d. Add imports ----
old_vue_import = "import { ref, computed, onMounted } from 'vue'"
new_vue_import = "import { ref, computed, onMounted } from 'vue'"
# Add ElMessage if not present
if "ElMessage" not in prdview:
    old_el_import = "import { ElMessageBox } from 'element-plus'"
    if old_el_import in prdview:
        prdview = prdview.replace(old_el_import, "import { ElMessage, ElMessageBox } from 'element-plus'")
    else:
        # Try without ElMessageBox
        old_el_import2 = "import { ElMessage } from 'element-plus'"
        if old_el_import2 not in prdview:
            # Add after any element-plus import
            old_any_el = "from 'element-plus'"
            if old_any_el in prdview:
                prdview = prdview.replace(old_any_el, "from 'element-plus'\nimport { ElMessage } from 'element-plus'")
    log("OK PrdView: added ElMessage import")

# Add updatePrd import
old_prd_import = "from '@/api/prd'"
if old_prd_import in prdview:
    if "updatePrd" not in prdview:
        prdview = prdview.replace(
            old_prd_import,
            "import { fetchPrdById, updatePrd } from '@/api/prd'"
        )
        log("OK PrdView: added updatePrd import")
    else:
        log("SKIP PrdView: updatePrd already imported")

# Add marked import
if "import { marked }" not in prdview:
    old_sc = "<script setup lang=\"ts\">"
    if old_sc in prdview:
        prdview = prdview.replace(
            old_sc,
            '<script setup lang="ts">\nimport { marked } from \'marked\''
        )
        log("OK PrdView: added marked import")

# ---- 3e. Add edit mode state and functions ----
# Find the <script setup> section end or a suitable insertion point
old_view_wiki = "const showWikiDialog = ref(false)"

new_view_wiki = """const showWikiDialog = ref(false)

// Edit mode
const editing = ref(false)
const saving = ref(false)
const editMarkdown = ref('')
const editRenderedPreview = computed(() => {
  if (!editMarkdown.value) return ''
  const html = marked.parse(editMarkdown.value, { async: false }) as string
  return typeof html === 'string' ? html : ''
})

function startEdit() {
  editing.value = true
  editMarkdown.value = prdStore.prd?.markdown || ''
}

function cancelEdit() {
  editing.value = false
  editMarkdown.value = ''
}

async function saveEdit() {
  saving.value = true
  try {
    const prdId = route.params.id as string
    const updated = await updatePrd(prdId, { markdown: editMarkdown.value })
    // Update store with saved data
    if (prdStore.prd) {
      prdStore.prd.markdown = updated.markdown
      if (updated.title) prdStore.prd.title = updated.title
    }
    editing.value = false
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}"""

if old_view_wiki in prdview and "const editing = ref(false)" not in prdview:
    prdview = prdview.replace(old_view_wiki, new_view_wiki)
    log("OK PrdView: added edit mode state + functions")
else:
    log("SKIP PrdView: edit mode already exists or anchor not found")

# ---- 3f. Add CSS for edit mode ----
old_style_close = "</style>"

new_edit_css = '''
/* Edit mode dual panel */
.prd-edit-dual {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.prd-edit-left,
.prd-edit-right {
  flex: 1;
  min-width: 0;
  overflow: auto;
}

.prd-edit-textarea {
  width: 100%;
  height: 100%;
  min-height: 600px;
  padding: 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.7;
  resize: none;
  outline: none;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.prd-edit-textarea:focus {
  border-color: var(--el-color-primary);
}
</style>'''

if old_style_close in prdview and ".prd-edit-dual" not in prdview:
    prdview = prdview.replace(old_style_close, new_edit_css)
    log("OK PrdView: added edit mode CSS")
else:
    log("SKIP PrdView: edit CSS already exists")

prdview_path.write_text(prdview, "utf-8")
log("\n=== Requirement 3 done ===")

# ── Summary ──
log("\n=== ALL DONE ===")
with open(ROOT / "__req123_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(LOG))
