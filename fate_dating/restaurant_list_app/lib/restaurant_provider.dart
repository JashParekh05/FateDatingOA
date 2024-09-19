import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'restaurant_service.dart';

final restaurantListProvider = FutureProvider<List<String>>((ref) async {
  return fetchRestaurants();
});

final searchQueryProvider = StateProvider<String>((ref) => "");
