/** 全量端点：与小程序 call(name, action, payload) 调用点一一对应 */
import { call, type CallOptions } from './client'
import type {
  CalendarData,
  CastResult,
  Channel,
  CheckinResult,
  Club,
  ClubPost,
  DormPost,
  HomeFeed,
  LostFoundItem,
  MessageList,
  MessagePrefs,
  MessageType,
  Overview,
  PageResult,
  Poll,
  ScanCard,
  SecondHandItem,
  VoteResults,
  WebHealth,
} from '@/types/models'

export const api = {
  health: async (): Promise<WebHealth> => {
    const resp = await fetch('/api/v1/web/health')
    const body = await resp.json()
    return body.data as WebHealth
  },

  homeFeed: (options?: CallOptions) => call<HomeFeed>('home', 'feed', {}, options),

  voteList: (tag: string, page: number, options?: CallOptions) =>
    call<PageResult<Poll>>('vote', 'list', { tag, page }, options),
  voteDetail: (pollId: string, options?: CallOptions) =>
    call<Poll>('vote', 'detail', { pollId }, options),
  voteResults: (pollId: string, options?: CallOptions) =>
    call<VoteResults>('vote', 'results', { pollId }, options),
  voteCast: (pollId: string, optionIds: string[]) =>
    call<CastResult>('vote', 'cast', { pollId, optionIds }, { loading: '提交中…' }),
  joinChain: (pollId: string, optionId: string) =>
    call<CastResult>('vote', 'joinChain', { pollId, optionId }, { loading: '提交中…' }),
  leaveChain: (pollId: string) =>
    call<{ left: boolean }>('vote', 'leaveChain', { pollId }, { loading: '提交中…' }),

  clubList: (category: string, keyword: string, page: number, options?: CallOptions) =>
    call<PageResult<Club>>('club', 'list', { category, keyword, page }, options),
  clubDetail: (clubId: string, options?: CallOptions) =>
    call<Club>('club', 'detail', { clubId }, options),
  clubPosts: (clubId: string, page = 0, options?: CallOptions) =>
    call<PageResult<ClubPost>>('club', 'posts', { clubId, page }, options),
  clubJoin: (clubId: string) =>
    call<{ joined: boolean; already: boolean }>('club', 'join', { clubId }, { loading: '提交中…' }),
  clubLeave: (clubId: string) =>
    call<{ left: boolean; already: boolean }>('club', 'leave', { clubId }, { loading: '提交中…' }),

  eventCalendar: (year: number, month: number, options?: CallOptions) =>
    call<CalendarData>('event', 'calendar', { year, month }, options),
  eventJoin: (eventId: string) =>
    call<{ joined: boolean; waitlisted: boolean; already: boolean }>(
      'event',
      'join',
      { eventId },
      { loading: '报名中…' },
    ),

  livingChannels: (options?: CallOptions) =>
    call<{ list: Channel[] }>('living', 'channels', {}, options),
  livingChannelPosts: (channelId: string, page = 0, options?: CallOptions) =>
    call<PageResult<DormPost>>('living', 'channelPosts', { channelId, page }, options),
  livingLostFound: (kind: string, page = 0, options?: CallOptions) =>
    call<PageResult<LostFoundItem>>('living', 'lostFound', { kind, page }, options),
  livingSecondHand: (page = 0, options?: CallOptions) =>
    call<PageResult<SecondHandItem>>('living', 'secondHand', { page }, options),

  scanCard: (key: string, options?: CallOptions) =>
    call<ScanCard>('scan', 'cardByCode', { key }, { loading: '查询中…', ...options }),
  scanCheckin: (key: string) =>
    call<CheckinResult>('scan', 'checkin', { key }, { loading: '打卡中…' }),

  meOverview: (options?: CallOptions) => call<Overview>('me', 'overview', {}, options),

  meMessages: (
    params: { cursor?: string; type?: MessageType; unreadOnly?: boolean } = {},
    options?: CallOptions,
  ) => call<MessageList>('me', 'messages', params, options),
  meMarkRead: (payload: { ids?: string[]; id?: string; all?: boolean }, options?: CallOptions) =>
    call<{ updated: number }>('me', 'markRead', payload, { silent: true, ...options }),
  meMessagePrefs: (prefs?: MessagePrefs, options?: CallOptions) =>
    call<{ prefs: MessagePrefs }>('me', 'messagePrefs', prefs ? { prefs } : {}, options),

  analyticsTrack: (event: string, props: Record<string, unknown> = {}) =>
    call<unknown>('analytics', 'track', { event, props }, { silent: true, noRetry: true }),
}
