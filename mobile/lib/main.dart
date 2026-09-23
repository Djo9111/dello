import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import 'core/config/app_config.dart';

void main() {
  runApp(const DelloApp());
}

class DelloApp extends StatelessWidget {
  const DelloApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Dello',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF00853F)),
        useMaterial3: true,
      ),
      home: const HealthCheckPage(),
    );
  }
}

class HealthCheckPage extends StatefulWidget {
  const HealthCheckPage({super.key});

  @override
  State<HealthCheckPage> createState() => _HealthCheckPageState();
}

class _HealthCheckPageState extends State<HealthCheckPage> {
  String _status = 'Vérification...';
  bool _isHealthy = false;

  @override
  void initState() {
    super.initState();
    _checkApi();
  }

  Future<void> _checkApi() async {
    setState(() => _status = 'Vérification...');

    // L'endpoint /health est à la racine, pas sous /api/v1
    final baseUrl = AppConfig.apiBaseUrl.replaceFirst('/api/v1', '');
    final dio = Dio(
      BaseOptions(
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
      ),
    );

    try {
      final response = await dio.get('$baseUrl/health');
      setState(() {
        _isHealthy = response.data['status'] == 'ok';
        _status = _isHealthy ? 'API joignable' : 'Réponse inattendue';
      });
    } on DioException catch (error) {
      setState(() {
        _isHealthy = false;
        _status = 'API injoignable : ${error.type.name}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              _isHealthy ? Icons.check_circle : Icons.error_outline,
              size: 64,
              color: _isHealthy ? Colors.green : Colors.orange,
            ),
            const SizedBox(height: 16),
            const Text('Dello', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(_status),
            const SizedBox(height: 4),
            Text(
              AppConfig.apiBaseUrl,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
            const SizedBox(height: 24),
            FilledButton(onPressed: _checkApi, child: const Text('Réessayer')),
          ],
        ),
      ),
    );
  }
}