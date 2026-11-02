/**
 * IEPP Workspace v2 — fail-closed adapter for official recommendation tools.
 * This module does not make network calls, create/approve projects, or run AI.
 * The real Site connector must map the authenticated official GET response
 * to a normalized snapshot; the raw response shape is not yet verified.
 */
import { buildPendingRecommendation, TEMPLATE_KEYS } from './recommendation-contract.mjs';

function nonEmpty(value, field, limit) {
  if (typeof value !== 'string' || !value.trim() || value.trim().length > limit) {
    throw new TypeError(field + ' must be a nonempty string of at most ' + limit + ' chars');
  }
  return value.trim();
}

function invalid(reason) {
  const error = new Error(reason);
  error.code = 'DRAFT_NOT_READY';
  return error;
}

export function chooseTemplate(goal) {
  if (/유튜브|유투브|youtube|쇼츠|shorts|영상\s*제작/i.test(goal)) return 'youtube';
  if (/사업|창업|고객|매출|판매|운영/i.test(goal)) return 'business';
  if (/조사|분석|연구|논문/i.test(goal)) return 'research';
  return 'creator';
}

export function readOwnedRequestSnapshot(raw, expectedId) {
  // Authenticated Site adapter, NOT user-provided chat text, must supply raw.
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw invalid('Site request snapshot missing');
  }
  const id = nonEmpty(raw.draft_id, 'snapshot.draft_id', 300);
  if (id !== expectedId) throw invalid('Site request ID differs');
  if (!Number.isSafeInteger(raw.revision) || raw.revision < 1) {
    throw invalid('Site request revision missing');
  }
  const goal = nonEmpty(raw.goal, 'snapshot.goal', 1600);
  if (raw.status !== undefined && raw.status !== 'requested') {
    throw invalid('Site request is not awaiting recommendation');
  }
  const modelPreference = typeof raw.model_preference === 'string' && raw.model_preference.trim()
    ? raw.model_preference.slice(0, 55) : '모델 미선택';
  return { id, revision:raw.revision, goal, modelPreference };
}

/**
 * Submit the structure for browser review, not for project creation.
 * No automatic retry or approval is permitted for stale revisions.
 */
export async function submitForHumanReview({
  draftId, templateKey, title, actualModelLabel, readOwnedRequest, savePending
} = {}) {
  const safeDraftId = nonEmpty(draftId, 'draftId', 300);
  const model = nonEmpty(actualModelLabel, 'actualModelLabel', 80);
  if (typeof readOwnedRequest !== 'function' || typeof savePending !== 'function') {
    throw new TypeError('Explicit readOwnedRequest and savePending adapters are required');
  }

  const raw = await readOwnedRequest({ draft_id:safeDraftId });
  const owned = readOwnedRequestSnapshot(raw, safeDraftId);
  const selected = templateKey ?? chooseTemplate(owned.goal);
  if (!TEMPLATE_KEYS.includes(selected)) throw new RangeError('Unsupported templateKey');
  const payload = buildPendingRecommendation({
    draftId:owned.id,
    expectedRevision:owned.revision,
    goal:owned.goal,
    title,
    templateKey:selected,
    requestedModelLabel:owned.modelPreference,
    actualModelLabel:model,
  });

  // savePending MUST be wired only to save_project_recommendation, never to
  // create_project, approve_task, agent execution, publishing or billing.
  const response = await savePending(payload);
  if (response == null || typeof response !== 'object' ||
      response.isError === true || response.ok === false || response.error) {
    throw invalid('The provider did not acknowledge saving a pending recommendation');
  }

  return {
    status:'recommendation_submission_acknowledged',
    draft_id:owned.id,
    sent_revision:owned.revision,
    template:selected,
    proposed_agents:payload.structure.agents.length,
    proposed_tasks:payload.structure.tasks.length,
    next_action:'사용자가 IEPP Lineage 사이트에서 초안을 검토하고 직접 프로젝트를 생성해야 합니다.',
    site_creation_confirmed:false,
    agent_execution_observed:false,
  };
}
