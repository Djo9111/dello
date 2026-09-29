import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../auth_controller.dart';

class VerifyPhoneScreen extends StatefulWidget {
  const VerifyPhoneScreen({super.key, required this.phoneNumber});

  /// Numéro déjà normalisé par le serveur au format +221XXXXXXXXX
  final String phoneNumber;

  @override
  State<VerifyPhoneScreen> createState() => _VerifyPhoneScreenState();
}

class _VerifyPhoneScreenState extends State<VerifyPhoneScreen> {
  static const _codeLength = 6;
  static const _resendDelay = 60;

  final _codeController = TextEditingController();

  Timer? _timer;
  int _secondsLeft = _resendDelay;
  bool _isSubmitting = false;
  bool _isResending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _startCountdown(_resendDelay);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _codeController.dispose();
    super.dispose();
  }

  /// Le serveur impose un délai entre deux codes : le compte à rebours
  /// évite de laisser l'utilisateur appuyer pour rien.
  void _startCountdown(int seconds) {
    _timer?.cancel();
    setState(() => _secondsLeft = seconds);

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() => _secondsLeft -= 1);
      if (_secondsLeft <= 0) timer.cancel();
    });
  }

    Future<void> _submit() async {
    if (_isSubmitting) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      await AuthController.instance.verifyPhone(
        phoneNumber: widget.phoneNumber,
        code: _codeController.text.trim(),
      );

      // AuthGate affiche déjà l'accueil, mais cet écran et celui de
      // l'inscription restent empilés par-dessus : on revient à la racine.
      if (mounted) {
        Navigator.of(context).popUntil((route) => route.isFirst);
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _codeController.clear();
      });
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Future<void> _resend() async {
    if (_isResending || _secondsLeft > 0) return;

    setState(() {
      _isResending = true;
      _error = null;
    });

    try {
      await AuthController.instance.resendCode(widget.phoneNumber);
      _startCountdown(_resendDelay);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Un nouveau code vient d\'être envoyé')),
        );
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      // Le serveur indique combien de temps attendre
      _startCountdown(error.retryAfterSeconds ?? _resendDelay);
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isResending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final canSubmit =
        _codeController.text.trim().length == _codeLength && !_isSubmitting;

    return Scaffold(
      appBar: AppBar(title: const Text('Vérification du numéro')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 16),
              Icon(
                Icons.sms_outlined,
                size: 56,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 20),
              Text(
                'Entrez le code à $_codeLength chiffres',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                'Envoyé par SMS au ${widget.phoneNumber}',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.inkSoft),
              ),
              const SizedBox(height: 32),
              TextField(
                controller: _codeController,
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                autofocus: true,
                autocorrect: false,
                enableSuggestions: false,
                autofillHints: const [AutofillHints.oneTimeCode],
                maxLength: _codeLength,
                enabled: !_isSubmitting,
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 12,
                ),
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(counterText: ''),
                onChanged: (_) => setState(() {}),
                onSubmitted: (_) => canSubmit ? _submit() : null,
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(_error!),
                ),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: canSubmit ? _submit : null,
                child: _isSubmitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Valider'),
              ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: _secondsLeft > 0 || _isResending ? null : _resend,
                child: Text(
                  _secondsLeft > 0
                      ? 'Renvoyer le code dans $_secondsLeft s'
                      : 'Renvoyer le code',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}