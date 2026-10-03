import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../auth_controller.dart';
import 'verify_phone_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _isSubmitting = false;
  bool _showPassword = false;
  String? _generalError;
  Map<String, String> _fieldErrors = {};

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

    Future<void> _submit() async {
    if (_isSubmitting) return;

    setState(() {
      _isSubmitting = true;
      _generalError = null;
      _fieldErrors = {};
    });

    final phone = _phoneController.text.trim();

    try {
      final verificationRequired =
          await AuthController.instance.startRegistration(
        phoneNumber: phone,
        fullName: _nameController.text.trim(),
        password: _passwordController.text,
      );

      if (!mounted) return;

      if (!verificationRequired) {
        // Compte créé et session ouverte : AuthGate affiche déjà l'accueil,
        // il reste à vider les écrans empilés par-dessus.
        Navigator.of(context).popUntil((route) => route.isFirst);
        return;
      }

      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => VerifyPhoneScreen(phoneNumber: _toE164(phone)),
        ),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _generalError = error.fieldErrors.isEmpty ? error.message : null;
        _fieldErrors = error.fieldErrors;
      });
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  /// Le serveur attend le même format pour la vérification que pour
  /// l'inscription, quel que soit ce que l'utilisateur a tapé.
  String _toE164(String input) {
    final digits = input.replaceAll(RegExp(r'[^0-9]'), '');
    final local = digits.length > 9 ? digits.substring(digits.length - 9) : digits;
    return '+221$local';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Créer un compte')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _nameController,
                textCapitalization: TextCapitalization.words,
                textInputAction: TextInputAction.next,
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Nom complet',
                  prefixIcon: const Icon(Icons.person_outline),
                  errorText: _fieldErrors['full_name'],
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                textInputAction: TextInputAction.next,
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Numéro de téléphone',
                  hintText: '77 123 45 67',
                  helperText: 'Un code de vérification y sera envoyé',
                  prefixIcon: const Icon(Icons.phone_outlined),
                  errorText: _fieldErrors['phone_number'],
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordController,
                obscureText: !_showPassword,
                autocorrect: false,
                enableSuggestions: false,
                enabled: !_isSubmitting,
                onSubmitted: (_) => _submit(),
                decoration: InputDecoration(
                  labelText: 'Mot de passe',
                  helperText: '10 caractères minimum',
                  prefixIcon: const Icon(Icons.lock_outline),
                  errorText: _fieldErrors['password'],
                  suffixIcon: IconButton(
                    icon: Icon(
                      _showPassword ? Icons.visibility_off : Icons.visibility,
                    ),
                    onPressed: () =>
                        setState(() => _showPassword = !_showPassword),
                  ),
                ),
              ),
              if (_generalError != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, size: 20),
                      const SizedBox(width: 10),
                      Expanded(child: Text(_generalError!)),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 24),
                            FilledButton(
                onPressed: _isSubmitting ? null : _submit,
                child: _isSubmitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Créer mon compte'),
              ),
              const SizedBox(height: 12),
                            const Text(
                'Votre numéro servira à vous joindre si votre document est retrouvé.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: AppTheme.inkSoft),
              ),
            ],
          ),
        ),
      ),
    );
  }
}