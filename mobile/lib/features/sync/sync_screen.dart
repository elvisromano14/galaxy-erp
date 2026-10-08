import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class SyncScreen extends StatefulWidget {
  const SyncScreen({super.key});

  @override
  State<SyncScreen> createState() => _SyncScreenState();
}

class _SyncScreenState extends State<SyncScreen> {
  bool _syncing = false;
  String? _statusMessage;

  Future<void> _sincronizar() async {
    setState(() {
      _syncing = true;
      _statusMessage = 'Descargando catálogos actualizados y tasas...';
    });

    try {
      final res = await ApiClient().dio.get('/api/v1/sync/catalogos?desde=0');
      final data = res.data;
      final prodsCount = (data['productos'] as List).length;
      final clisCount = (data['clientes'] as List).length;

      setState(() {
        _statusMessage = '¡Sincronización exitosa!\n'
            '• Productos descargados: $prodsCount\n'
            '• Clientes descargados: $clisCount\n'
            '• Token de sync: ${data['sync_token']}\n'
            '• Modo offline listo para operar en calle.';
      });
    } catch (e) {
      setState(() {
        _statusMessage = 'Error en la sincronización. Verifique conexión a red.';
      });
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Preventa y Sincronización Móvil', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppTheme.textDark)),
          const Text('Gestión de datos fuera de línea y operaciones pendientes', style: TextStyle(color: AppTheme.textMuted, fontSize: 13)),
          const SizedBox(height: 24),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.cloud_sync_rounded, size: 36, color: AppTheme.primary),
                      SizedBox(width: 12),
                      Text('Estado del Dispositivo', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Presione el botón para actualizar precios, clientes y existencias antes de salir a la ruta.'),
                  const SizedBox(height: 20),
                  ElevatedButton.icon(
                    onPressed: _syncing ? null : _sincronizar,
                    icon: _syncing
                        ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Icon(Icons.sync_rounded),
                    label: Text(_syncing ? 'SINCRONIZANDO...' : 'SINCRONIZAR AHORA'),
                  ),
                  if (_statusMessage != null) ...[
                    const SizedBox(height: 20),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF1F5F9),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(_statusMessage!, style: const TextStyle(fontSize: 13, height: 1.4, color: AppTheme.textDark)),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
