import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import 'auth_provider.dart';

/// 注册：学号 + 学校邮箱验证码（PRD U-001）
class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  final _formKey = GlobalKey<FormState>();
  final _sid = TextEditingController();
  final _email = TextEditingController();
  final _nick = TextEditingController();
  final _pwd = TextEditingController();
  final _code = TextEditingController();
  bool _loading = false;
  bool _codeSent = false;
  String? _error;
  String? _tip;

  @override
  void dispose() {
    for (final c in [_sid, _email, _nick, _pwd, _code]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _sendCode() async {
    if (_email.text.trim().isEmpty) {
      setState(() => _error = '请输入学校邮箱');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final r = await ApiService.sendCode(_email.text.trim());
      setState(() {
        _codeSent = true;
        _tip = '验证码已发送${r['dev_code'] != null ? '（开发模式：${r['dev_code']}）' : ''}';
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
    setState(() => _loading = false);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    final ok = await ref.read(authStateProvider).register(
          studentId: _sid.text.trim(),
          email: _email.text.trim(),
          password: _pwd.text.trim(),
          nickname: _nick.text.trim(),
          emailCode: _code.text.trim(),
        );
    if (!mounted) return;
    setState(() => _loading = false);
    if (ok) {
      context.go('/home');
    } else {
      setState(() => _error = ref.read(authStateProvider).error ?? '注册失败');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(title: const Text('注册')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('使用学号与学校邮箱完成注册',
                    style: TextStyle(fontSize: 13, color: GoQDColors.textSecondary)),
                const SizedBox(height: 20),
                TextFormField(
                  controller: _sid,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: '学号'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? '请输入学号' : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                      labelText: '学校邮箱', hintText: 'xxx@qd.baoan.edu.cn'),
                  validator: (v) => (v == null || !v.contains('@')) ? '请输入有效邮箱' : null,
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _code,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: '邮箱验证码'),
                        validator: (v) => (v == null || v.length != 6) ? '6 位验证码' : null,
                      ),
                    ),
                    const SizedBox(width: 10),
                    OutlinedButton(
                      onPressed: _loading ? null : _sendCode,
                      style: OutlinedButton.styleFrom(minimumSize: const Size(100, 50)),
                      child: Text(_codeSent ? '重发' : '获取验证码'),
                    ),
                  ],
                ),
                if (_tip != null) ...[
                  const SizedBox(height: 8),
                  Text(_tip!, style: const TextStyle(fontSize: 12, color: GoQDColors.accent)),
                ],
                const SizedBox(height: 14),
                TextFormField(
                  controller: _nick,
                  decoration: const InputDecoration(labelText: '昵称'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? '请输入昵称' : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _pwd,
                  obscureText: true,
                  decoration: const InputDecoration(
                      labelText: '密码', hintText: '至少 8 位，含字母和数字'),
                  validator: (v) {
                    if (v == null || v.length < 8) return '密码至少 8 位';
                    if (!RegExp(r'[A-Za-z]').hasMatch(v) || !RegExp(r'\d').hasMatch(v)) {
                      return '需同时包含字母和数字';
                    }
                    return null;
                  },
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: GoQDColors.danger, fontSize: 13)),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('注册并进入'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
