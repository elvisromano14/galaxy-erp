import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class InventarioScreen extends StatefulWidget {
  const InventarioScreen({super.key});

  @override
  State<InventarioScreen> createState() => _InventarioScreenState();
}

class _InventarioScreenState extends State<InventarioScreen> {
  List<dynamic> _saldos = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _cargarSaldos();
  }

  Future<void> _cargarSaldos() async {
    setState(() => _loading = true);
    try {
      final res = await ApiClient().dio.get('/api/v1/inventario/saldos');
      setState(() => _saldos = res.data);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('Control de Inventario', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppTheme.textDark)),
                  Text('Existencias en tiempo real y kardex inmutable', style: TextStyle(color: AppTheme.textMuted, fontSize: 13)),
                ],
              ),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.swap_horiz_rounded, size: 18),
                label: const Text('NUEVO TRASLADO'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Expanded(
            child: Card(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _saldos.isEmpty
                      ? const Center(child: Text('No hay registros de inventario.', style: TextStyle(color: AppTheme.textMuted)))
                      : ListView.separated(
                          itemCount: _saldos.length,
                          separatorBuilder: (_, __) => const Divider(height: 1, color: Color(0xFFE2E8F0)),
                          itemBuilder: (context, index) {
                            final s = _saldos[index];
                            return ListTile(
                              leading: const CircleAvatar(
                                backgroundColor: Color(0xFFECFDF5),
                                child: Icon(Icons.inventory_rounded, color: AppTheme.accent),
                              ),
                              title: Text('Producto ID: ${s['product_id']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                              subtitle: Text('Almacén: ${s['warehouse_id']}'),
                              trailing: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF1F5F9),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: Text(
                                  '${s['cantidad']} UND',
                                  style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textDark),
                                ),
                              ),
                            );
                          },
                        ),
            ),
          ),
        ],
      ),
    );
  }
}
