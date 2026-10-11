/// 后端接口路径集中定义（对应 server/app/api/v1）
class ApiEndpoints {
  ApiEndpoints._();

  static const String baseUrl = String.fromEnvironment(
    'GOQD_API_BASE',
    defaultValue: 'http://localhost:8000',
  );

  static const String apiV1 = '/api/v1';

  // 认证
  static const String sendCode = '$apiV1/auth/send-code';
  static const String register = '$apiV1/auth/register';
  static const String login = '$apiV1/auth/login';
  static const String refresh = '$apiV1/auth/refresh';
  static const String logout = '$apiV1/auth/logout';

  // 首页
  static const String homeFeed = '$apiV1/home/feed';

  // 投票
  static const String votes = '$apiV1/votes';
  static const String todayPoll = '$apiV1/votes/today';
  static String pollDetail(int id) => '$apiV1/votes/$id';
  static String castVote(int id) => '$apiV1/votes/$id/cast';
  static String pollResults(int id) => '$apiV1/votes/$id/results';
  static String pollComments(int id) => '$apiV1/votes/$id/comments';
  static String joinGroup(int id) => '$apiV1/votes/$id/join';

  // 社团
  static const String clubs = '$apiV1/clubs';
  static String clubDetail(int id) => '$apiV1/clubs/$id';
  static String clubJoin(int id) => '$apiV1/clubs/$id/join';
  static String clubPosts(int id) => '$apiV1/clubs/$id/posts';
  static String likePost(int id) => '$apiV1/clubs/posts/$id/like';

  // 活动
  static const String events = '$apiV1/events';
  static const String calendar = '$apiV1/events/calendar';
  static const String myCas = '$apiV1/events/me/cas';
  static String eventJoin(int id) => '$apiV1/events/$id/join';

  // 住宿生活
  static const String dormChannels = '$apiV1/living/channels';
  static String channelPosts(int id) => '$apiV1/living/channels/$id/posts';
  static const String lostFound = '$apiV1/living/lost-found';
  static const String secondHand = '$apiV1/living/second-hand';

  // OMEGA / NFC
  static String nfcCard(String cardId) => '$apiV1/nfc/$cardId';
  static const String nfcTap = '$apiV1/nfc/tap';
  static const String nfcCheckins = '$apiV1/nfc/me/checkins';

  // 用户
  static const String me = '$apiV1/users/me';
  static const String myVotes = '$apiV1/users/me/votes';
  static const String myClubs = '$apiV1/users/me/clubs';
  static const String myEvents = '$apiV1/users/me/events';
  static const String myNotifications = '$apiV1/users/me/notifications';
  static const String readNotifications = '$apiV1/users/me/notifications/read';

  // 勋章
  static const String badges = '$apiV1/badges';

  // 推送
  static const String pushDevices = '$apiV1/push/devices';
}
