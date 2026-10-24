/** 与云函数出参一一对应的数据结构（见 bala-miniapp/docs/API.md） */

export interface ApiEnvelope<T> {
  ok: boolean
  data: T | null
  message: string
  code?: string
}

export interface PageResult<T> {
  list: T[]
  hasMore: boolean
}

export type PollType = 'single' | 'multi' | 'pk' | 'ranking' | 'groupbuy'

export interface PollOption {
  optionId: string
  label: string
  sortOrder?: number
  count?: number
}

export interface Poll {
  _id: string
  title: string
  description: string
  pollType: PollType
  status?: string
  tag?: string
  category?: string
  topicTags?: string[]
  coverUrl?: string
  startAt?: string | null
  endAt?: string | null
  allowChange?: boolean
  maxChoices?: number | null
  maxParticipants?: number | null
  totalVotes: number
  participantCount?: number
  options: PollOption[]
  myChoice?: string[]
  hasVoted?: boolean
  isChanged?: boolean
  canChange?: boolean
  joined?: boolean
  joinedOptionId?: string | null
  isFull?: boolean
}

export interface VoteResults {
  pollId: string
  total: number
  options: Array<PollOption & { percent: number }>
  groups?: unknown[]
}

export interface CastResult {
  voted: boolean
  changed: boolean
  optionIds: string[]
  newBadges?: Badge[]
}

export interface Club {
  _id: string
  name: string
  description: string
  logoUrl?: string
  coverUrl?: string
  category?: string
  isVerified: boolean
  memberCount: number
  followerCount?: number
  heatScore: number
  joined?: boolean
}

export interface ClubPost {
  _id: string
  clubId: string
  title: string
  content: string
  images: string[]
  isPinned: boolean
  likeCount: number
  publishedAt?: string | null
}

export interface EventInfo {
  _id: string
  title: string
  description?: string
  coverUrl?: string
  location?: string
  organizerType?: string
  organizerId?: string | null
  startAt?: string
  endAt?: string
  signupDeadline?: string | null
  maxParticipants?: number | null
  status?: string
  casType?: string | null
  participantCount: number
  registered?: boolean
  waitlisted?: boolean
}

export interface Banner {
  _id: string
  title: string
  imageUrl: string
  targetRoute: string
}

export type HomeSectionType = 'banner' | 'todayPoll' | 'quickEntries' | 'hotPolls' | 'events' | 'clubs'

export interface QuickEntry {
  key: string
  label: string
  icon: string
  to: string
}

export interface HomeSection {
  id: string
  type: HomeSectionType
  title: string
  enabled: boolean
  config: { limit?: number; items?: QuickEntry[] }
}

export interface HomeFeed {
  sections?: HomeSection[]
  banners: Banner[]
  todayPoll: Poll | null
  hotPolls: Poll[]
  events: EventInfo[]
  clubs: Club[]
}

export interface CalendarData {
  days: Array<{ date: string; count: number }>
  events: EventInfo[]
}

export interface Channel {
  _id: string
  name: string
  scope: string
  building: string
  floor: string
  room: string
}

export interface DormPost {
  _id: string
  channelId: string
  content: string
  images: string[]
  likeCount: number
  createdAt?: string
}

export interface LostFoundItem {
  _id: string
  kind: 'lost' | 'found'
  title: string
  description: string
  location: string
  contact: string
  images: string[]
  isResolved: boolean
  createdAt?: string
}

export interface SecondHandItem {
  _id: string
  title: string
  description: string
  price: number | null
  images: string[]
  contact: string
  isSold: boolean
  createdAt?: string
}

export interface LocationRule {
  type: string
  name: string
  desc: string
}

export interface ScanCard {
  cardId: string
  locationDesc: string
  locationType: string
  targetType?: string | null
  targetId?: string | null
  checked: boolean
  tapCount: number
  uniqueCards: number
  rules: LocationRule[]
}

export interface Badge {
  code: string
  name: string
  description?: string
  iconUrl?: string
  icon?: string
  rarity?: string
  rule?: { type?: string; count?: number }
  earnedAt?: string | null
  unlocked?: boolean
}

export interface CheckinResult {
  checked: boolean
  firstTime: boolean
  cardId: string
  uniqueCards: number
  newBadges: Badge[]
  target?: { type?: string | null; id?: string | null }
}

export type MessageType =
  | 'event_change'
  | 'event_cancelled'
  | 'poll_result'
  | 'owner_response'
  | 'deadline'

export interface MessageInfo {
  _id: string
  type: MessageType
  title: string
  content: string
  refType: string
  refId: string
  readAt: string | null
  createdAt: string
}

export interface MessageList {
  list: MessageInfo[]
  hasMore: boolean
  unread: number
}

export interface MessagePrefs {
  eventChange: boolean
  eventCancel: boolean
  pollResult: boolean
  ownerResponse: boolean
  deadline: boolean
}

export interface Overview {
  stats: {
    voteCount: number
    checkinCount: number
    badgeCount: number
    badgeTotal: number
  }
  badges: Badge[]
  recentVotes: Array<{
    pollId: string
    title: string
    optionIds: string[]
    createdAt?: string
  }>
  recentCheckins: Array<{
    cardId: string
    tapCount: number
    firstTapAt?: string
    lastTapAt?: string
  }>
}

export interface Session {
  identity: string
  token: string
}

export interface WebHealth {
  mode: 'cloud' | 'local'
  cloudReady: boolean
  cloudEnv: string
  cloudWriteEnabled?: boolean
}
