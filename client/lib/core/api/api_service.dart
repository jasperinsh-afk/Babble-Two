import '../../shared/models.dart';
import '../network/api_client.dart';
import '../network/api_endpoints.dart';

/// 统一 API 调用层（所有返回已解包为 data）
class ApiService {
  ApiService._();

  // ── 认证 ──

  static Future<Map<String, dynamic>> sendCode(String email) async {
    final r = await ApiClient.post(ApiEndpoints.sendCode, data: {'email': email});
    return (r ?? {}) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> register({
    required String studentId,
    required String email,
    required String password,
    required String nickname,
    required String emailCode,
    String? grade,
    String? dormitory,
  }) async {
    final r = await ApiClient.post(ApiEndpoints.register, data: {
      'student_id': studentId,
      'email': email,
      'password': password,
      'nickname': nickname,
      'email_code': emailCode,
      if (grade != null) 'grade': grade,
      if (dormitory != null) 'dormitory': dormitory,
    });
    return (r ?? {}) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> login(String studentId, String password) async {
    final r = await ApiClient.post(ApiEndpoints.login,
        data: {'student_id': studentId, 'password': password});
    return (r ?? {}) as Map<String, dynamic>;
  }

  // ── 首页 ──

  static Future<HomeFeed> homeFeed() async {
    final r = await ApiClient.get(ApiEndpoints.homeFeed);
    return HomeFeed.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  // ── 投票 ──

  static Future<Page<Poll>> pollList({
    String? tag,
    String? status,
    int offset = 0,
    int limit = 20,
  }) async {
    final r = await ApiClient.get(ApiEndpoints.votes, query: {
      if (tag != null) 'tag': tag,
      if (status != null) 'status': status,
      'offset': offset,
      'limit': limit,
    });
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, Poll.fromJson);
  }

  static Future<Poll?> todayPoll() async {
    final r = await ApiClient.get(ApiEndpoints.todayPoll);
    if (r == null) return null;
    return Poll.fromJson(r as Map<String, dynamic>);
  }

  static Future<Poll> pollDetail(int id) async {
    final r = await ApiClient.get(ApiEndpoints.pollDetail(id));
    return Poll.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<Poll> castVote(int id, List<int> optionIds, {bool change = false}) async {
    final r = change
        ? await ApiClient.put(ApiEndpoints.castVote(id), data: {'option_ids': optionIds})
        : await ApiClient.post(ApiEndpoints.castVote(id), data: {'option_ids': optionIds});
    return Poll.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<VoteResult> pollResults(int id) async {
    final r = await ApiClient.get(ApiEndpoints.pollResults(id));
    return VoteResult.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<Page<PollComment>> pollComments(int id, {int offset = 0}) async {
    final r = await ApiClient.get(ApiEndpoints.pollComments(id),
        query: {'offset': offset, 'limit': 20});
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, PollComment.fromJson);
  }

  static Future<PollComment> addComment(int id, String content) async {
    final r = await ApiClient.post(ApiEndpoints.pollComments(id),
        data: {'content': content});
    return PollComment.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<Poll> joinGroup(int id, int optionId) async {
    final r = await ApiClient.post(ApiEndpoints.joinGroup(id),
        query: {'option_id': optionId});
    return Poll.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<void> leaveGroup(int id) =>
      ApiClient.delete(ApiEndpoints.joinGroup(id));

  // ── 社团 ──

  static Future<Page<Club>> clubList({String? category, String keyword = '', int offset = 0}) async {
    final r = await ApiClient.get(ApiEndpoints.clubs, query: {
      if (category != null) 'category': category,
      'keyword': keyword,
      'offset': offset,
      'limit': 20,
    });
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, Club.fromJson);
  }

  static Future<Club> clubDetail(int id) async {
    final r = await ApiClient.get(ApiEndpoints.clubDetail(id));
    return Club.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<void> joinClub(int id) => ApiClient.post(ApiEndpoints.clubJoin(id));

  static Future<void> leaveClub(int id) =>
      ApiClient.delete(ApiEndpoints.clubJoin(id));

  static Future<Page<ClubPost>> clubPosts(int id, {int offset = 0}) async {
    final r = await ApiClient.get(ApiEndpoints.clubPosts(id),
        query: {'offset': offset, 'limit': 20});
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, ClubPost.fromJson);
  }

  static Future<void> createPost(int clubId, String content, {String? title}) =>
      ApiClient.post(ApiEndpoints.clubPosts(clubId),
          data: {'content': content, if (title != null) 'title': title});

  // ── 活动 ──

  static Future<Page<Event>> eventList({DateTime? start, int offset = 0}) async {
    final r = await ApiClient.get(ApiEndpoints.events, query: {
      if (start != null) 'start': start.toIso8601String(),
      'offset': offset,
      'limit': 20,
    });
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, Event.fromJson);
  }

  static Future<List<CalendarDay>> calendar(int year, int month) async {
    final r = await ApiClient.get(ApiEndpoints.calendar,
        query: {'year': year, 'month': month});
    if (r is List) return r.map((e) => CalendarDay.fromJson(e)).toList();
    return [];
  }

  static Future<Event> joinEvent(int id) async {
    final r = await ApiClient.post(ApiEndpoints.eventJoin(id));
    return Event.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<void> cancelEvent(int id) =>
      ApiClient.delete(ApiEndpoints.eventJoin(id));

  static Future<List<CasRecord>> myCas() async {
    final r = await ApiClient.get(ApiEndpoints.myCas);
    if (r is List) return r.map((e) => CasRecord.fromJson(e)).toList();
    return [];
  }

  static Future<List<Event>> myEvents() async {
    final r = await ApiClient.get(ApiEndpoints.myEvents);
    if (r is List) return r.map((e) => Event.fromJson(e)).toList();
    return [];
  }

  // ── 住宿生活 ──

  static Future<List<DormChannel>> dormChannels() async {
    final r = await ApiClient.get(ApiEndpoints.dormChannels);
    if (r is List) return r.map((e) => DormChannel.fromJson(e)).toList();
    return [];
  }

  static Future<Page<DormPost>> dormPosts(int channelId, {int offset = 0}) async {
    final r = await ApiClient.get(ApiEndpoints.channelPosts(channelId),
        query: {'offset': offset, 'limit': 20});
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, DormPost.fromJson);
  }

  static Future<void> createDormPost(int channelId, String content) =>
      ApiClient.post(ApiEndpoints.channelPosts(channelId),
          data: {'channel_id': channelId, 'content': content});

  static Future<Page<LostFoundItem>> lostFound({String? kind}) async {
    final r = await ApiClient.get(ApiEndpoints.lostFound,
        query: {if (kind != null) 'kind': kind});
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, LostFoundItem.fromJson);
  }

  static Future<Page<SecondHandItem>> secondHand() async {
    final r = await ApiClient.get(ApiEndpoints.secondHand);
    return Page.fromJson((r ?? {}) as Map<String, dynamic>, SecondHandItem.fromJson);
  }

  // ── OMEGA / NFC ──

  static Future<NfcCard> nfcCard(String cardId) async {
    final r = await ApiClient.get(ApiEndpoints.nfcCard(cardId));
    return NfcCard.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<Map<String, dynamic>> nfcTap(String cardId, bool installed) async {
    final r = await ApiClient.post(ApiEndpoints.nfcTap, data: {
      'card_id': cardId,
      'device_type': 'android',
      'app_installed': installed,
    });
    return (r ?? {}) as Map<String, dynamic>;
  }

  static Future<NfcCheckin> nfcCheckins() async {
    final r = await ApiClient.get(ApiEndpoints.nfcCheckins);
    return NfcCheckin.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  // ── 用户 ──

  static Future<User> me() async {
    final r = await ApiClient.get(ApiEndpoints.me);
    return User.fromJson((r ?? {}) as Map<String, dynamic>);
  }

  static Future<List<NotificationItem>> notifications({bool unread = false}) async {
    final r = await ApiClient.get(ApiEndpoints.myNotifications,
        query: {'unread': unread});
    if (r is Map && r['items'] is List) {
      return (r['items'] as List).map((e) => NotificationItem.fromJson(e)).toList();
    }
    return [];
  }

  static Future<List<Badge>> badges() async {
    final r = await ApiClient.get(ApiEndpoints.badges);
    if (r is List) {
      return r.map((e) => Badge.fromJson(e['badge'] ?? e)).toList();
    }
    return [];
  }

  static Future<List<Club>> myClubs() async {
    final r = await ApiClient.get(ApiEndpoints.myClubs);
    if (r is List) return r.map((e) => Club.fromJson(e)).toList();
    return [];
  }
}
