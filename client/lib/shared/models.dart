import 'dart:convert';

// ────────────────────────────────────────────
// 枚举
// ────────────────────────────────────────────

enum PollType { single, multi, pk, ranking, groupbuy }

extension PollTypeX on PollType {
  String get value => name;
  String get label => switch (this) {
        PollType.single => '单选',
        PollType.multi => '多选',
        PollType.pk => 'PK',
        PollType.ranking => '排序',
        PollType.groupbuy => '接龙',
      };
  static PollType parse(String? v) =>
      PollType.values.firstWhere((e) => e.name == v, orElse: () => PollType.single);
}

enum PollStatus { draft, scheduled, active, closed, archived, withdrawn }

extension PollStatusX on PollStatus {
  static PollStatus parse(String? v) => PollStatus.values
      .firstWhere((e) => e.name == v, orElse: () => PollStatus.draft);
  bool get isOpen => this == PollStatus.active;
}

enum PollTag { news, campus, meme, group }

extension PollTagX on PollTag {
  String get label => switch (this) {
        PollTag.news => '时事',
        PollTag.campus => '校园',
        PollTag.meme => '热梗',
        PollTag.group => '接龙',
      };
  String get value => name;
}

enum ClubCategory { academic, sports, art, charity, interest, other }

extension ClubCategoryX on ClubCategory {
  String get label => switch (this) {
        ClubCategory.academic => '学术',
        ClubCategory.sports => '体育',
        ClubCategory.art => '艺术',
        ClubCategory.charity => '公益',
        ClubCategory.interest => '兴趣',
        ClubCategory.other => '其他',
      };
  static ClubCategory parse(String? v) => ClubCategory.values
      .firstWhere((e) => e.name == v, orElse: () => ClubCategory.other);
}

enum NfcTargetType { vote, club, event, download }

extension NfcTargetTypeX on NfcTargetType {
  static NfcTargetType parse(String? v) => NfcTargetType.values
      .firstWhere((e) => e.name == v, orElse: () => NfcTargetType.download);
}

// ────────────────────────────────────────────
// 基础解析工具
// ────────────────────────────────────────────

String _str(dynamic v) => v?.toString() ?? '';
int _int(dynamic v) => v is int ? v : int.tryParse(_str(v)) ?? 0;
double _dbl(dynamic v) => v is num ? v.toDouble() : double.tryParse(_str(v)) ?? 0;
bool _bool(dynamic v) => v == true || v == 1 || _str(v) == 'true';
DateTime? _date(dynamic v) => v == null ? null : DateTime.tryParse(_str(v));

List<T> _list<T>(dynamic v, T Function(dynamic) f) =>
    v is List ? v.map(f).toList() : <T>[];

// ────────────────────────────────────────────
// 用户
// ────────────────────────────────────────────

class User {
  final int id;
  final String studentId;
  final String email;
  final String nickname;
  final String? avatarUrl;
  final String? bio;
  final String? grade;
  final String? dormitory;
  final String role;

  User({
    required this.id,
    required this.studentId,
    required this.email,
    required this.nickname,
    this.avatarUrl,
    this.bio,
    this.grade,
    this.dormitory,
    this.role = 'student',
  });

  factory User.fromJson(Map<String, dynamic> j) => User(
        id: _int(j['id']),
        studentId: _str(j['student_id']),
        email: _str(j['email']),
        nickname: _str(j['nickname']),
        avatarUrl: j['avatar_url']?.toString(),
        bio: j['bio']?.toString(),
        grade: j['grade']?.toString(),
        dormitory: j['dormitory']?.toString(),
        role: _str(j['role']).isEmpty ? 'student' : _str(j['role']),
      );
}

// ────────────────────────────────────────────
// 投票
// ────────────────────────────────────────────

class PollOption {
  final int id;
  final String label;
  final int sortOrder;
  final int voteCount;
  final double percent;

  PollOption({
    required this.id,
    required this.label,
    this.sortOrder = 0,
    this.voteCount = 0,
    this.percent = 0,
  });

  factory PollOption.fromJson(Map<String, dynamic> j) => PollOption(
        id: _int(j['id']),
        label: _str(j['label']),
        sortOrder: _int(j['sort_order']),
        voteCount: _int(j['vote_count']),
        percent: _dbl(j['percent']),
      );
}

class Poll {
  final int id;
  final String title;
  final String? description;
  final PollType type;
  final PollStatus status;
  final String? category;
  final PollTag? tag;
  final DateTime? startAt;
  final DateTime? endAt;
  final bool allowChange;
  final int? maxChoices;
  final int? maxParticipants;
  final String? coverUrl;
  final List<PollOption> options;
  final int totalVotes;
  final List<int>? myChoice;
  final bool hasVoted;
  final bool isChanged;
  final int? remainingSeconds;
  final int participantCount;

  Poll({
    required this.id,
    required this.title,
    this.description,
    this.type = PollType.single,
    this.status = PollStatus.draft,
    this.category,
    this.tag,
    this.startAt,
    this.endAt,
    this.allowChange = true,
    this.maxChoices,
    this.maxParticipants,
    this.coverUrl,
    this.options = const [],
    this.totalVotes = 0,
    this.myChoice,
    this.hasVoted = false,
    this.isChanged = false,
    this.remainingSeconds,
    this.participantCount = 0,
  });

  factory Poll.fromJson(Map<String, dynamic> j) => Poll(
        id: _int(j['id']),
        title: _str(j['title']),
        description: j['description']?.toString(),
        type: PollTypeX.parse(j['poll_type']?.toString()),
        status: PollStatusX.parse(j['status']?.toString()),
        category: j['category']?.toString(),
        tag: j['tag'] == null
            ? null
            : PollTag.values.firstWhere((e) => e.name == j['tag'],
                orElse: () => PollTag.campus),
        startAt: _date(j['start_at']),
        endAt: _date(j['end_at']),
        allowChange: _bool(j['allow_change']) || j['allow_change'] == null,
        maxChoices: j['max_choices'] == null ? null : _int(j['max_choices']),
        maxParticipants:
            j['max_participants'] == null ? null : _int(j['max_participants']),
        coverUrl: j['cover_url']?.toString(),
        options: _list(j['options'], (e) => PollOption.fromJson(e)),
        totalVotes: _int(j['total_votes']),
        myChoice: j['my_choice'] == null
            ? null
            : _list(j['my_choice'], (e) => _int(e)),
        hasVoted: _bool(j['has_voted']),
        isChanged: _bool(j['is_changed']),
        remainingSeconds:
            j['remaining_seconds'] == null ? null : _int(j['remaining_seconds']),
        participantCount: _int(j['participant_count']),
      );

  String get remainingText {
    final s = remainingSeconds;
    if (s == null) return '';
    if (s <= 0) return '已结束';
    if (s < 3600) return '剩余 ${s ~/ 60} 分钟';
    if (s < 86400) return '剩余 ${s ~/ 3600} 小时';
    return '剩余 ${s ~/ 86400} 天';
  }
}

class VoteResult {
  final int pollId;
  final String title;
  final int totalVotes;
  final List<PollOption> options;
  final Map<String, dynamic>? breakdown;
  final bool closed;

  VoteResult({
    required this.pollId,
    required this.title,
    required this.totalVotes,
    required this.options,
    this.breakdown,
    this.closed = false,
  });

  factory VoteResult.fromJson(Map<String, dynamic> j) => VoteResult(
        pollId: _int(j['poll_id']),
        title: _str(j['title']),
        totalVotes: _int(j['total_votes']),
        options: _list(j['options'], (e) => PollOption.fromJson(e)),
        breakdown: j['breakdown'] as Map<String, dynamic>?,
        closed: _bool(j['closed']),
      );
}

class PollComment {
  final int id;
  final int pollId;
  final int userId;
  final String authorNickname;
  final String content;
  final int likeCount;
  final DateTime? createdAt;

  PollComment({
    required this.id,
    required this.pollId,
    required this.userId,
    required this.authorNickname,
    required this.content,
    this.likeCount = 0,
    this.createdAt,
  });

  factory PollComment.fromJson(Map<String, dynamic> j) => PollComment(
        id: _int(j['id']),
        pollId: _int(j['poll_id']),
        userId: _int(j['user_id']),
        authorNickname: _str(j['author_nickname']),
        content: _str(j['content']),
        likeCount: _int(j['like_count']),
        createdAt: _date(j['created_at']),
      );
}

// ────────────────────────────────────────────
// 社团
// ────────────────────────────────────────────

class Club {
  final int id;
  final String name;
  final String? description;
  final String? logoUrl;
  final String? coverUrl;
  final ClubCategory category;
  final bool isVerified;
  final int memberCount;
  final int heatScore;
  final bool isMember;
  final String? myRole;

  Club({
    required this.id,
    required this.name,
    this.description,
    this.logoUrl,
    this.coverUrl,
    this.category = ClubCategory.other,
    this.isVerified = false,
    this.memberCount = 0,
    this.heatScore = 0,
    this.isMember = false,
    this.myRole,
  });

  factory Club.fromJson(Map<String, dynamic> j) => Club(
        id: _int(j['id']),
        name: _str(j['name']),
        description: j['description']?.toString(),
        logoUrl: j['logo_url']?.toString(),
        coverUrl: j['cover_url']?.toString(),
        category: ClubCategoryX.parse(j['category']?.toString()),
        isVerified: _bool(j['is_verified']),
        memberCount: _int(j['member_count']),
        heatScore: _int(j['heat_score']),
        isMember: _bool(j['is_member']) || _bool(j['is_following']),
        myRole: j['my_role']?.toString(),
      );
}

class ClubPost {
  final int id;
  final int clubId;
  final String? clubName;
  final String? title;
  final String content;
  final List<String> images;
  final bool isPinned;
  final int likeCount;
  final int commentCount;
  final DateTime? createdAt;

  ClubPost({
    required this.id,
    required this.clubId,
    this.clubName,
    this.title,
    required this.content,
    this.images = const [],
    this.isPinned = false,
    this.likeCount = 0,
    this.commentCount = 0,
    this.createdAt,
  });

  factory ClubPost.fromJson(Map<String, dynamic> j) => ClubPost(
        id: _int(j['id']),
        clubId: _int(j['club_id']),
        clubName: j['club_name']?.toString(),
        title: j['title']?.toString(),
        content: _str(j['content']),
        images: j['images'] == null
            ? const []
            : (jsonDecode(j['images'].toString()) as List)
                .map((e) => e.toString())
                .toList(),
        isPinned: _bool(j['is_pinned']),
        likeCount: _int(j['like_count']),
        commentCount: _int(j['comment_count']),
        createdAt: _date(j['created_at']),
      );
}

// ────────────────────────────────────────────
// 活动
// ────────────────────────────────────────────

class Event {
  final int id;
  final String title;
  final String? description;
  final String? coverUrl;
  final String? location;
  final String organizerType;
  final String? organizerName;
  final DateTime? startAt;
  final DateTime? endAt;
  final int? maxParticipants;
  final int participantCount;
  final String status;
  final bool registeredByMe;
  final bool isWaitlist;

  Event({
    required this.id,
    required this.title,
    this.description,
    this.coverUrl,
    this.location,
    this.organizerType = 'club',
    this.organizerName,
    this.startAt,
    this.endAt,
    this.maxParticipants,
    this.participantCount = 0,
    this.status = 'active',
    this.registeredByMe = false,
    this.isWaitlist = false,
  });

  factory Event.fromJson(Map<String, dynamic> j) => Event(
        id: _int(j['id']),
        title: _str(j['title']),
        description: j['description']?.toString(),
        coverUrl: j['cover_url']?.toString(),
        location: j['location']?.toString(),
        organizerType: _str(j['organizer_type']).isEmpty
            ? 'club'
            : _str(j['organizer_type']),
        organizerName: j['organizer_name']?.toString(),
        startAt: _date(j['start_at']),
        endAt: _date(j['end_at']),
        maxParticipants:
            j['max_participants'] == null ? null : _int(j['max_participants']),
        participantCount: _int(j['participant_count']),
        status: _str(j['status']).isEmpty ? 'active' : _str(j['status']),
        registeredByMe: _bool(j['registered_by_me']),
        isWaitlist: _bool(j['is_waitlist']),
      );

  bool get isFull => status == 'full';
}

class CasRecord {
  final int id;
  final String title;
  final String casType;
  final String role;
  final DateTime? happenedAt;

  CasRecord({
    required this.id,
    required this.title,
    required this.casType,
    this.role = 'participant',
    this.happenedAt,
  });

  factory CasRecord.fromJson(Map<String, dynamic> j) => CasRecord(
        id: _int(j['id']),
        title: _str(j['title']),
        casType: _str(j['cas_type']),
        role: _str(j['role']).isEmpty ? 'participant' : _str(j['role']),
        happenedAt: _date(j['happened_at']),
      );
}

class CalendarDay {
  final DateTime date;
  final int count;
  final List<Event> events;

  CalendarDay({required this.date, required this.count, this.events = const []});

  factory CalendarDay.fromJson(Map<String, dynamic> j) => CalendarDay(
        date: _date(j['date']) ?? DateTime.now(),
        count: _int(j['count']),
        events: _list(j['events'], (e) => Event.fromJson(e)),
      );
}

// ────────────────────────────────────────────
// 住宿生活
// ────────────────────────────────────────────

class DormChannel {
  final int id;
  final String name;
  final String scope;

  DormChannel({required this.id, required this.name, required this.scope});

  factory DormChannel.fromJson(Map<String, dynamic> j) => DormChannel(
        id: _int(j['id']),
        name: _str(j['name']),
        scope: _str(j['scope']),
      );

  String get scopeLabel => switch (scope) {
        'room' => '宿舍',
        'floor' => '楼层',
        _ => '全校',
      };
}

class DormPost {
  final int id;
  final int channelId;
  final String authorNickname;
  final String content;
  final List<String> images;
  final int likeCount;
  final int replyCount;
  final DateTime? createdAt;

  DormPost({
    required this.id,
    required this.channelId,
    required this.authorNickname,
    required this.content,
    this.images = const [],
    this.likeCount = 0,
    this.replyCount = 0,
    this.createdAt,
  });

  factory DormPost.fromJson(Map<String, dynamic> j) => DormPost(
        id: _int(j['id']),
        channelId: _int(j['channel_id']),
        authorNickname: _str(j['author_nickname']),
        content: _str(j['content']),
        images: j['images'] == null
            ? const []
            : (jsonDecode(j['images'].toString()) as List)
                .map((e) => e.toString())
                .toList(),
        likeCount: _int(j['like_count']),
        replyCount: _int(j['reply_count']),
        createdAt: _date(j['created_at']),
      );
}

class LostFoundItem {
  final int id;
  final String kind;
  final String title;
  final String? description;
  final String? location;
  final String? contact;
  final bool isResolved;
  final DateTime? createdAt;

  LostFoundItem({
    required this.id,
    required this.kind,
    required this.title,
    this.description,
    this.location,
    this.contact,
    this.isResolved = false,
    this.createdAt,
  });

  factory LostFoundItem.fromJson(Map<String, dynamic> j) => LostFoundItem(
        id: _int(j['id']),
        kind: _str(j['kind']).isEmpty ? 'lost' : _str(j['kind']),
        title: _str(j['title']),
        description: j['description']?.toString(),
        location: j['location']?.toString(),
        contact: j['contact']?.toString(),
        isResolved: _bool(j['is_resolved']),
        createdAt: _date(j['created_at']),
      );
}

class SecondHandItem {
  final int id;
  final String title;
  final String? description;
  final int? price;
  final String? contact;
  final bool isSold;
  final DateTime? createdAt;

  SecondHandItem({
    required this.id,
    required this.title,
    this.description,
    this.price,
    this.contact,
    this.isSold = false,
    this.createdAt,
  });

  factory SecondHandItem.fromJson(Map<String, dynamic> j) => SecondHandItem(
        id: _int(j['id']),
        title: _str(j['title']),
        description: j['description']?.toString(),
        price: j['price'] == null ? null : _int(j['price']),
        contact: j['contact']?.toString(),
        isSold: _bool(j['is_sold']),
        createdAt: _date(j['created_at']),
      );

  String get priceText => price == null ? '面议' : '¥${(price! / 100).toStringAsFixed(2)}';
}

// ────────────────────────────────────────────
// OMEGA / NFC
// ────────────────────────────────────────────

class NfcCard {
  final String cardId;
  final NfcTargetType targetType;
  final int? targetId;
  final String? targetUrl;
  final String? locationDesc;

  NfcCard({
    required this.cardId,
    required this.targetType,
    this.targetId,
    this.targetUrl,
    this.locationDesc,
  });

  factory NfcCard.fromJson(Map<String, dynamic> j) => NfcCard(
        cardId: _str(j['card_id']),
        targetType: NfcTargetTypeX.parse(j['target_type']?.toString()),
        targetId: j['target_id'] == null ? null : _int(j['target_id']),
        targetUrl: j['target_url']?.toString(),
        locationDesc: j['location_desc']?.toString(),
      );

  /// App 内路由
  String get route {
    switch (targetType) {
      case NfcTargetType.vote:
        return '/vote/$targetId';
      case NfcTargetType.club:
        return '/club/$targetId';
      case NfcTargetType.event:
        return '/event/$targetId';
      case NfcTargetType.download:
        return '/nfc';
    }
  }
}

class NfcCheckin {
  final int uniqueCards;
  final int totalTaps;
  final List<NfcCheckinCard> cards;

  NfcCheckin({required this.uniqueCards, required this.totalTaps, this.cards = const []});

  factory NfcCheckin.fromJson(Map<String, dynamic> j) => NfcCheckin(
        uniqueCards: _int(j['unique_cards']),
        totalTaps: _int(j['total_taps']),
        cards: _list(j['cards'], (e) => NfcCheckinCard.fromJson(e)),
      );
}

class NfcCheckinCard {
  final String cardId;
  final int tapCount;
  final DateTime? firstTapAt;

  NfcCheckinCard({required this.cardId, this.tapCount = 0, this.firstTapAt});

  factory NfcCheckinCard.fromJson(Map<String, dynamic> j) => NfcCheckinCard(
        cardId: _str(j['card_id']),
        tapCount: _int(j['tap_count']),
        firstTapAt: _date(j['first_tap_at']),
      );
}

// ────────────────────────────────────────────
// 勋章 / 通知
// ────────────────────────────────────────────

class Badge {
  final int id;
  final String code;
  final String name;
  final String? description;
  final String? iconUrl;
  final String rarity;
  final DateTime? earnedAt;

  Badge({
    required this.id,
    required this.code,
    required this.name,
    this.description,
    this.iconUrl,
    this.rarity = 'normal',
    this.earnedAt,
  });

  factory Badge.fromJson(Map<String, dynamic> j) => Badge(
        id: _int(j['id']),
        code: _str(j['code']),
        name: _str(j['name']),
        description: j['description']?.toString(),
        iconUrl: j['icon_url']?.toString(),
        rarity: _str(j['rarity']).isEmpty ? 'normal' : _str(j['rarity']),
        earnedAt: _date(j['earned_at']),
      );

  bool get earned => earnedAt != null;
}

class NotificationItem {
  final int id;
  final String type;
  final String title;
  final String? content;
  final String? refType;
  final int? refId;
  final bool isRead;
  final DateTime? createdAt;

  NotificationItem({
    required this.id,
    required this.type,
    required this.title,
    this.content,
    this.refType,
    this.refId,
    this.isRead = false,
    this.createdAt,
  });

  factory NotificationItem.fromJson(Map<String, dynamic> j) => NotificationItem(
        id: _int(j['id']),
        type: _str(j['type']),
        title: _str(j['title']),
        content: j['content']?.toString(),
        refType: j['ref_type']?.toString(),
        refId: j['ref_id'] == null ? null : _int(j['ref_id']),
        isRead: _bool(j['is_read']),
        createdAt: _date(j['created_at']),
      );
}

// ────────────────────────────────────────────
// 首页聚合
// ────────────────────────────────────────────

class Banner {
  final int id;
  final String title;
  final String subtitle;
  final String target;

  Banner({required this.id, required this.title, required this.subtitle, required this.target});

  factory Banner.fromJson(Map<String, dynamic> j) => Banner(
        id: _int(j['id']),
        title: _str(j['title']),
        subtitle: _str(j['subtitle']),
        target: _str(j['target']),
      );
}

class HomeFeed {
  final List<Banner> banners;
  final Poll? todayPoll;
  final List<Poll> hotPolls;
  final List<Event> recommendedEvents;
  final List<Club> featuredClubs;

  HomeFeed({
    this.banners = const [],
    this.todayPoll,
    this.hotPolls = const [],
    this.recommendedEvents = const [],
    this.featuredClubs = const [],
  });

  factory HomeFeed.fromJson(Map<String, dynamic> j) => HomeFeed(
        banners: _list(j['banners'], (e) => Banner.fromJson(e)),
        todayPoll: j['today_poll'] == null ? null : Poll.fromJson(j['today_poll']),
        hotPolls: _list(j['hot_polls'], (e) => Poll.fromJson(e)),
        recommendedEvents: _list(j['recommended_events'], (e) => Event.fromJson(e)),
        featuredClubs: _list(j['featured_clubs'], (e) => Club.fromJson(e)),
      );
}

// ────────────────────────────────────────────
// 分页
// ────────────────────────────────────────────

class Page<T> {
  final List<T> items;
  final int total;
  final int offset;
  final int limit;
  final bool hasMore;

  Page({
    required this.items,
    required this.total,
    this.offset = 0,
    this.limit = 20,
    this.hasMore = false,
  });

  factory Page.fromJson(
    Map<String, dynamic> j,
    T Function(Map<String, dynamic>) f,
  ) =>
      Page<T>(
        items: _list(j['items'], (e) => f(e)),
        total: _int(j['total']),
        offset: _int(j['offset']),
        limit: _int(j['limit']),
        hasMore: _bool(j['has_more']),
      );
}
