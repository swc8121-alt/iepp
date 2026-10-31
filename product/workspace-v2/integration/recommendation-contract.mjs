/**
 * IEPP Workspace v2 — pure, server-side proposal payload builder.
 * No API calls, permissions, approval, scheduling, or agent execution.
 * The output matches the save_project_recommendation input fields, subject to
 * verification against a real server get_project_recommendation_request read.
 */

const TEMPLATES = Object.freeze({
  creator: {
    title: '콘텐츠 제작 프로젝트',
    roles: [
      ['lead', null, '콘텐츠 기획 총괄', '콘텐츠 방향과 검토 순서를 정리합니다.', '기획안'],
      ['research', 'lead', '자료 조사 도우미', '주제 관련 근거와 자료를 조사합니다.', '출처 목록'],
      ['writing', 'lead', '콘텐츠 초안 도우미', '승인된 자료를 바탕으로 초안을 제안합니다.', '콘텐츠 초안'],
    ],
    tasks: [
      ['plan', null, 'lead', '콘텐츠 목표와 대상 정리'],
      ['sources', 'plan', 'research', '자료와 출처 검토'],
      ['draft', 'sources', 'writing', '콘텐츠 초안 작성 및 사용자 검토'],
    ],
  },
  business: {
    title: '1인 사업 운영 프로젝트',
    roles: [
      ['lead', null, '사업 운영 총괄', '업무 목표와 의사결정 항목을 정리합니다.', '운영 계획'],
      ['research', 'lead', '시장 조사 도우미', '경쟁사와 고객 의견을 조사합니다.', '비교표'],
      ['report', 'lead', '업무 보고 도우미', '진행 내용과 결과를 요약합니다.', '업무 보고서'],
    ],
    tasks: [
      ['plan', null, 'lead', '사업 목표와 우선순위 정리'],
      ['research', 'plan', 'research', '시장 및 고객 정보 조사'],
      ['report', 'research', 'report', '결과 요약과 사용자 검토'],
    ],
  },
  research: {
    title: '자료 조사 프로젝트',
    roles: [
      ['lead', null, '조사 총괄', '질문과 조사 범위를 정합니다.', '조사 계획'],
      ['collect', 'lead', '자료 수집 도우미', '출처와 근거를 수집합니다.', '근거 목록'],
      ['review', 'lead', '근거 검토 도우미', '근거의 한계와 요약을 정리합니다.', '검토 보고서'],
    ],
    tasks: [
      ['scope', null, 'lead', '조사 질문과 범위 확정'],
      ['collect', 'scope', 'collect', '자료와 출처 정리'],
      ['review', 'collect', 'review', '근거 평가 및 사용자 검토'],
    ],
  },
});

export const TEMPLATE_KEYS = Object.freeze(Object.keys(TEMPLATES));

function requiredString(value, field, maxLength) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new TypeError(`${field}: a nonempty string is required`);
  }
  const text = value.trim();
  if (text.length > maxLength) {
    throw new RangeError(`${field}: exceeds ${maxLength} characters`);
  }
  return text;
}

/**
 * Call only after reading the signed-in user's request from the official
 * get_project_recommendation_request tool. Never guess draft_id or revision.
 */
export function buildPendingRecommendation({
  draftId,
  expectedRevision,
  goal,
  title,
  templateKey,
  requestedModelLabel = '모델 미선택',
  actualModelLabel,
}) {
  const draft_id = requiredString(draftId, 'draftId', 300);
  if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 1) {
    throw new TypeError('expectedRevision: positive integer required');
  }
  const cleanGoal = requiredString(goal, 'goal', 1600);
  if (!Object.hasOwn(TEMPLATES, templateKey)) {
    throw new RangeError('templateKey: unknown preset');
  }
  const preset = TEMPLATES[templateKey];
  const projectTitle = title == null ? preset.title : requiredString(title, 'title', 100);
  const preferredModel = requiredString(requestedModelLabel, 'requestedModelLabel', 55);
  const actualModel = requiredString(actualModelLabel, 'actualModelLabel', 80);

  return {
    draft_id,
    expected_revision: expectedRevision,
    structure: {
      version: 1,
      title: projectTitle,
      goal: cleanGoal,
      agents: preset.roles.map(([key, parent_key, name, role, output_format]) => ({
        key,
        parent_key,
        name,
        role,
        instructions: `역할 범위: ${role} 기록 또는 자료가 없으면 미확인으로 표시하고, 실제 실행·외부 발송·결제를 수행하지 마세요. 사용자 승인 전에는 계획 초안만 제안합니다.`,
        output_format,
        model_label: `추천 표시: ${preferredModel} (미배정)`,
      })),
      tasks: preset.tasks.map(([key, parent_key, agent_key, taskTitle]) => ({
        key,
        parent_key,
        agent_key,
        title: taskTitle,
        brief: `프로젝트의 목표(goal)를 기준으로 검토할 초안 작업입니다. 작업: ${taskTitle}. 실행·승인·자동 예약은 발생하지 않았습니다.`,
      })),
      // One supported lineage catalog entry. This does NOT establish a new connection.
      connections: ['iepp-lineage'],
    },
    explanation: '목표에 맞춘 역할 3개와 작업 초안 3개입니다. 웹 화면에서 내용을 검토한 후 사용자가 직접 프로젝트를 생성해야 합니다. 에이전트 실행 및 외부 작업은 수행하지 않았습니다.',
    model_label: actualModel,
  };
}

/**
 * A UI status classifier; only explicit observed receipts imply observed run.
 * L1 record hash consistency is not execution continuity or original identity.
 */
export function classifyVerification({
  recordCheck = 'unknown',
  executionContinuity = 'unobserved',
  externalReceiptVerified = false,
} = {}) {
  const record = recordCheck === 'match' ? 'record-match'
    : recordCheck === 'mismatch' ? 'record-mismatch' : 'record-unknown';
  const execution = externalReceiptVerified === true && executionContinuity === 'observed'
    ? 'observed-with-receipt' : 'not-independently-observed';
  return { record, execution, originalIdentity: 'not-verified' };
}